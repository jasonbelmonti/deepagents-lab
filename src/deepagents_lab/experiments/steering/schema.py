"""Source conversations, model-authored pairs, and persisted vector records."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*")
    @classmethod
    def reject_blank_text(cls, value):
        # Whitespace can encode Markdown/Python structure. Validate blank values
        # without rewriting source messages, corrections or proposed responses.
        if isinstance(value, str) and not value.strip():
            raise ValueError("Text must contain a non-whitespace character.")
        return value


class Message(StrictModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str = Field(min_length=1)


class SteeringEvent(StrictModel):
    event_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,100}$")
    group_id: str = Field(min_length=1, description="Original conversation/task; keep paraphrases together.")
    family: str = Field(min_length=1, description="Human relevance label; never shown to the capture model.")
    messages: list[Message] = Field(min_length=3)
    synthetic: bool = False

    @model_validator(mode="after")
    def steering_is_last(self):
        if self.messages[-1].role != "user" or not any(m.role == "assistant" for m in self.messages[:-1]):
            raise ValueError("End each event at the user's steering message, after an assistant attempt.")
        return self


class SteeringPair(StrictModel):
    problem: str = Field(min_length=12, max_length=1200, description="Context-specific behavior or omission that needed steering.")
    correction: str = Field(min_length=12, max_length=1200, description="Actionable adjustment requested by the user.")


class CapturedExample(StrictModel):
    event: SteeringEvent
    pair: SteeringPair
    origin: Literal["authored_fixture", "model"]
    capture_model: str
    embedding_id: str
    x: list[float]
    y: list[float]

    @model_validator(mode="after")
    def vectors_are_valid(self):
        from math import isfinite

        for vector in (self.x, self.y):
            if not vector or not all(isfinite(v) for v in vector) or not any(v != 0 for v in vector):
                raise ValueError("Embeddings must be finite, nonzero vectors.")
        if len(self.x) != len(self.y):
            raise ValueError("X and Y must use the same embedding dimensions.")
        return self
