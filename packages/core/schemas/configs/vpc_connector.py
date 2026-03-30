from pydantic import BaseModel, Field


class VpcConnectorSubnet(BaseModel):
    name: str
    project_id: str | None = None


class VpcConnectorConfig(BaseModel):
    region: str
    network: str | None = None
    ip_cidr_range: str | None = None
    subnet: VpcConnectorSubnet | None = None
    min_throughput: int = Field(default=200, ge=200, le=1000)
    max_throughput: int = Field(default=1000, ge=200, le=1000)
    machine_type: str = "e2-micro"
    min_instances: int = Field(default=2, ge=2, le=9)
    max_instances: int = Field(default=10, ge=3, le=10)
