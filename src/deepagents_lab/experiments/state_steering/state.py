"""One deterministic state representation for historical and runtime checkpoints."""
import json

from .schema import ObservableState

# Conservative byte bound: standard text-embedding-3 tokenization uses no more
# tokens than UTF-8 bytes. Reject oversized inputs instead of silently truncating
# requirements. This pilot intentionally supports short, complete checkpoints.
MAX_STATE_BYTES = 7000


def build_state(history, proposed_response):
    return ObservableState(history=history, proposed_response=proposed_response)


def state_from_event(event):
    """Freeze immediately before steering; require an assistant response checkpoint."""
    if event.messages[-2].role != "assistant":
        raise ValueError("Expected an assistant response immediately before user steering.")
    return build_state(event.messages[:-2], event.messages[-2].content)


def state_text(state: ObservableState) -> str:
    # Never accept StateExample here: labels and the later steering have no route
    # into the serialized predictor input. Both training and serving call this.
    if not isinstance(state, ObservableState):
        raise TypeError("Serialize an ObservableState, not an annotated example.")
    text = json.dumps(state.model_dump(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if len(text.encode("utf-8")) > MAX_STATE_BYTES:
        raise ValueError(f"State exceeds the {MAX_STATE_BYTES}-byte pilot limit; no truncation was applied.")
    return text
