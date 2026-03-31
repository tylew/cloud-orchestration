"""Unified environment variable model for compute nodes."""

from typing import Literal

from pydantic import BaseModel, model_validator


class EnvVarEntry(BaseModel):
    name: str
    type: Literal["value", "secret"]
    value: str | None = None
    secret: str | None = None
    version: str = "latest"

    @model_validator(mode="after")
    def validate_type_fields(self):
        if self.type == "value" and self.secret is not None:
            raise ValueError("type='value' entries must not set 'secret'")
        if self.type == "secret" and self.value is not None:
            raise ValueError("type='secret' entries must not set 'value'")
        return self
