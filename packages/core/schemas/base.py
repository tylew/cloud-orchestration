"""Core schema models derived from GCP_SCHEMA.md S1-S3."""

import re
from typing import Any

from pydantic import BaseModel, Field, model_validator

from .enums import NodeType, OutputType, Protocol
from .configs import TYPE_TO_CONFIG


class NodeInput(BaseModel):
    name: str
    source: str
    protocol: Protocol | None = None


class NodeOutput(BaseModel):
    name: str
    type: OutputType | None = None
    value: str | None = None


class IamBlock(BaseModel):
    service_account: str | None = None
    roles: list[str] = []


class InvokerBinding(BaseModel):
    service_account: str
    description: str | None = None


class AccessorBinding(BaseModel):
    service_account: str


class BaseNode(BaseModel, extra="allow"):
    slug: str = ""
    name: str
    type: NodeType
    depends_on: list[str] = []
    inputs: list[NodeInput] = []
    outputs: list[NodeOutput] = []
    iam: IamBlock | None = None
    invoker_bindings: list[InvokerBinding] = []
    accessor_bindings: list[AccessorBinding] = []
    config: dict[str, Any] | BaseModel = Field(default_factory=dict)

    @model_validator(mode="after")
    def resolve_config_and_validate(self):
        # Validate name is kebab-case
        if not re.match(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$", self.name):
            raise ValueError(f"Node name {self.name!r} must be kebab-case")

        # Resolve polymorphic config — strict (D-05)
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
