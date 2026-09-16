"""Matched synthetic checkpoints for wiring checks, not empirical efficacy claims."""
from ..steering.fixture import make_fixtures
from .schema import StateExample
from .state import build_state, state_from_event

GOOD = {
    "experiment-evidence": (
        "The experiment measured a 12% latency reduction; results/experiment.json contains the measurements.",
        "Implemented the feature. The experiment measured a 12% latency reduction. Evidence: results/experiment.json.",
    ),
    "test-execution": (
        "The regression command finished successfully: 24 tests passed, 0 failed.",
        "Implemented the feature and ran the regression suite: 24 passed, 0 failed.",
    ),
    "scope-control": (
        "The diff contains only the requested feature changes. The billing module is unchanged.",
        "The requested change is complete; the patch is limited to its original scope.",
    ),
    "source-attribution": (
        "The reference at https://example.com/reference states that the operation accepts JSON.",
        "The operation accepts JSON. Supporting source: https://example.com/reference.",
    ),
    "response-format": (
        "The implementation is complete, its checks passed, and no follow-up work remains.",
        "- Implemented the requested change.\n- Relevant checks passed.\n- No follow-up work remains.",
    ),
}


def make_state_fixtures():
    """66 examples: 30 steer, 30 matched compliant controls, 6 later scope changes.

    A group's positive/control pair always travels together across data splits.
    Negative labels are authored judgments, never inferred from user silence.
    """
    examples = []
    for fixture in make_fixtures():
        event = fixture.event
        state = state_from_event(event)
        if event.family == "response-format":
            state = build_state(state.history, "\n\n".join([
                "Implementation is complete. " + sentence for sentence in (
                    "First I inspected the repository.", "Then I considered the architecture.",
                    "Next I investigated the interfaces.", "I updated the implementation.",
                    "I reviewed the resulting changes.", "This concludes the detailed handoff.",
                )
            ]))
        needed = event.family != "new-requirement"
        examples.append(StateExample(
            sample_id=event.event_id, group_id=event.group_id, state=state,
            needs_intervention=needed, problem=fixture.pair.problem,
            correction=fixture.pair.correction, family=event.family,
            source_event_id=event.event_id, synthetic=True,
            assessment=("The visible requirement is unmet at this checkpoint." if needed else
                        "The original task is complete. The migration guide is new scope introduced later."),
        ))
        if needed:
            evidence, response = GOOD[event.family]
            examples.append(StateExample(
                sample_id=event.event_id + "-compliant", group_id=event.group_id,
                state=build_state([event.messages[0], {"role": "assistant", "content": evidence}], response),
                needs_intervention=False, assessment="The visible requirement is satisfied by the supplied evidence and response.",
                synthetic=True,
            ))
    return examples
