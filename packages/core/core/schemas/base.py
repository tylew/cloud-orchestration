"""Core schema models — GCP resource definitions and blueprint envelope."""

import re
from typing import Any

from pydantic import BaseModel, Field, model_validator

from .enums import NodeType
from .configs import TYPE_TO_CONFIG


class BaseNode(BaseModel, extra="allow"):
    slug: str = ""
    name: str
    type: NodeType
    depends_on: list[str] = []
    config: dict[str, Any] | BaseModel = Field(default_factory=dict)

    @model_validator(mode="after")
    def resolve_config_and_validate(self):
        if not re.match(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$", self.name):
            raise ValueError(f"Node name {self.name!r} must be kebab-case")

        config_cls = TYPE_TO_CONFIG.get(self.type)
        if config_cls is None:
            raise ValueError(f"Unknown node type: {self.type!r}")
        if isinstance(self.config, dict):
            self.config = config_cls.model_validate(self.config)
        if not isinstance(self.config, BaseModel):
            raise ValueError(f"Config must be a Pydantic model, got {type(self.config).__name__}")

        return self


# --- Envelope ---

class NetworkingConfig(BaseModel, extra="allow"):
    vpc: str | None = None
    subnet: str | None = None
    vpc_connector: str | None = None


class BackendConfig(BaseModel):
    type: str = "gcs"
    bucket: str = ""
    prefix: str = ""


class GlobalConfig(BaseModel, extra="allow"):
    project_id: str
    region: str
    environment: str
    naming_convention: str = "${environment}-${node.name}"
    labels: dict[str, str] = {}
    networking: NetworkingConfig | None = None
    backend: BackendConfig | None = None


class Metadata(BaseModel):
    created_at: str | None = None
    updated_at: str | None = None
    author: str | None = None


class Envelope(BaseModel):
    schema_: str | None = Field(default=None, alias="$schema")
    version: str = "1.0.0"
    global_: GlobalConfig = Field(alias="global")
    nodes: list[BaseNode] = []
    metadata: Metadata | None = None

    model_config = {"populate_by_name": True}
