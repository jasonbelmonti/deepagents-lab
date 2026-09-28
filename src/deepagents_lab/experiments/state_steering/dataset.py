"""Reviewed JSONL ingestion, capture conversion, and S/Y embedding preparation."""
from pathlib import Path

from .schema import EmbeddedState, StateExample
from .state import state_from_event, state_text


def from_capture(record, *, needs_intervention: bool, assessment: str):
    """A researcher decides whether intervention was justified at the old checkpoint.

    Steering itself is not this label: newly introduced scope can be a negative.
    Captured X and Y text remain available for audit even in that case.
    """
    return StateExample(
        sample_id=record.event.event_id, group_id=record.event.group_id,
        state=state_from_event(record.event), needs_intervention=needs_intervention,
        assessment=assessment, problem=record.pair.problem, correction=record.pair.correction,
        family=record.event.family, source_event_id=record.event.event_id,
        synthetic=record.event.synthetic,
    )


def validate_examples(examples):
    examples = list(examples)
    if not examples or len({e.sample_id for e in examples}) != len(examples):
        raise ValueError("Provide nonempty examples with unique sample IDs.")
    seen = set()
    for example in examples:
        text = state_text(example.state)
        if text in seen:
            raise ValueError("Duplicate observable states must be reconciled before evaluation.")
        seen.add(text)
    return examples


def load_examples(path):
    return validate_examples([StateExample.model_validate_json(line)
                              for line in Path(path).read_text().splitlines() if line.strip()])


def embed_examples(examples, embedder):
    """One bounded call per example, with S and (for positives) Y; X is never embedded."""
    examples = validate_examples(examples)
    for example in examples:
        if example.correction and len(example.correction.encode("utf-8")) > 7000:
            raise ValueError("Correction exceeds the 7000-byte pilot limit.")
    records = []
    for example in examples:
        texts = [state_text(example.state)]
        if example.needs_intervention:
            texts.append(example.correction)
        vectors = embedder.embed(texts)
        records.append(EmbeddedState(example=example, embedding_id=embedder.identity,
                                     s=vectors[0].tolist(), y=vectors[1].tolist() if len(texts) == 2 else None))
    return records
