"""Separate runtime observations from retrospective researcher annotations."""
from math import isfinite
from typing import Literal

from pydantic import Field, model_validator

from ..steering.schema import Message, StrictModel

STATE_FORMAT = "final-response-v1"


class ObservableState(StrictModel):
    format: Literal["final-response-v1"] = STATE_FORMAT
    history: list[Message] = Field(min_length=1)
    proposed_response: str = Field(min_length=1)


class StateExample(StrictModel):
    sample_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,100}$")
    group_id: str = Field(min_length=1)
    state: ObservableState
    needs_intervention: bool
    assessment: str = Field(min_length=12, description="Reviewed justification for the intervention label.")
    problem: str | None = Field(default=None, min_length=12)
    correction: str | None = Field(default=None, min_length=12)
    family: str | None = Field(default=None, min_length=1)
    source_event_id: str | None = None
    synthetic: bool = False

    @model_validator(mode="after")
    def positive_has_target(self):
        if self.needs_intervention and not all((self.problem, self.correction, self.family)):
            raise ValueError("Intervention examples require problem, correction and family annotations.")
        return self


class EmbeddedState(StrictModel):
    example: StateExample
    embedding_id: str = Field(min_length=1)
    s: list[float]
    y: list[float] | None = None

    @model_validator(mode="after")
    def vectors_match_label(self):
        if self.example.needs_intervention != (self.y is not None):
            raise ValueError("Only intervention examples have a correction target vector.")
        for vector in (self.s, self.y):
            if vector is not None and (not vector or not all(isfinite(v) for v in vector)
                                       or not any(v != 0 for v in vector)):
                raise ValueError("Embeddings must be finite, nonzero vectors.")
        if self.y is not None and len(self.s) != len(self.y):
            raise ValueError("State and correction dimensions must agree.")
        return self
