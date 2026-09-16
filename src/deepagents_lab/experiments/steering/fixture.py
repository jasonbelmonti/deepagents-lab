"""Authored synthetic conversations. An illustrative wiring corpus, not efficacy evidence."""
from dataclasses import dataclass

from .schema import SteeringEvent, SteeringPair


@dataclass(frozen=True)
class Fixture:
    event: SteeringEvent
    pair: SteeringPair


# Six contexts with different wording; one context is held out together across families.
CONTEXTS = (
    ("search ranking", "Implemented the requested change.", "Before finishing,"),
    ("checkout flow", "The feature is ready for review.", "You still need to"),
    ("report export", "Work is complete and the patch is ready.", "Please go back and"),
    ("notification routing", "The requested update is finished.", "The handoff needs you to"),
    ("image ingestion", "I completed the implementation.", "One thing is missing:"),
    ("document indexing", "The change is done.", "We cannot close this until you"),
)

# Conditions and actions are deliberately visible. Never pass these annotations to LIVE capture.
FAMILIES = (
    (
        "experiment-evidence",
        "Implement {task}, run the experiment, and include the measured results in the handoff.",
        "The experiment ran; its measurements are saved in results/experiment.json.",
        "include the experiment measurements and link the evidence file.",
        "The completion handoff for {task} omits required experiment measurements even though results exist.",
        "Read the saved experiment results and report the measurements with a link to the evidence.",
    ),
    (
        "test-execution",
        "Implement {task} and run the relevant regression tests before declaring completion.",
        "I inspected the test code but have not executed the regression suite.",
        "run the regression tests and report their actual outcome.",
        "The agent declared {task} complete while the required regression tests remained unexecuted.",
        "Execute the relevant regression tests and report the observed outcome before reporting completion.",
    ),
    (
        "scope-control",
        "Make only the requested {task} change; leave unrelated modules unchanged.",
        "I also reformatted the unrelated billing module while implementing the feature.",
        "remove the unrelated billing formatting changes from this patch.",
        "The {task} patch includes unrelated formatting changes despite the task's explicit scope limit.",
        "Remove the unrelated formatting changes while preserving the requested feature implementation.",
    ),
    (
        "source-attribution",
        "Investigate {task} and provide source links supporting each factual conclusion.",
        "I read the sources and prepared conclusions, but the handoff includes no source links.",
        "attach supporting source links to the conclusions.",
        "The research handoff about {task} states conclusions without the supporting source links requested.",
        "Attach the relevant source links to each factual conclusion in the research handoff.",
    ),
    (
        "response-format",
        "Implement {task}; give the final status in exactly three concise bullet points.",
        "The final status is a twelve-paragraph narrative about implementation details.",
        "rewrite that status as exactly three concise bullet points.",
        "The final status for {task} is a lengthy narrative despite the user's three-bullet format requirement.",
        "Rewrite the status as exactly three concise bullet points while preserving the material outcome.",
    ),
    (
        "new-requirement",
        "Implement {task} and report completion. No documentation update is requested.",
        "The requested implementation is complete and verified.",
        "also add a migration guide; I am adding that requirement now.",
        "After the original {task} was completed, the user expanded scope to include a migration guide.",
        "Add a migration guide as newly requested work; preserve the completed implementation.",
    ),
)


def make_fixtures() -> list[Fixture]:
    result = []
    for index, (task, final, prefix) in enumerate(CONTEXTS):
        for family, request, evidence, steering, problem, correction in FAMILIES:
            event = SteeringEvent(
                event_id=f"{family}-{index}", group_id=f"scenario-{index}", family=family, synthetic=True,
                messages=[
                    {"role": "user", "content": request.format(task=task)},
                    {"role": "assistant", "content": evidence},
                    {"role": "assistant", "content": final},
                    {"role": "user", "content": f"{prefix} {steering}"},
                ],
            )
            result.append(Fixture(event, SteeringPair(problem=problem.format(task=task), correction=correction)))
    return result
