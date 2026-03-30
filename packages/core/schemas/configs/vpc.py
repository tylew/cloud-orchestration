from pydantic import BaseModel, Field


class VpcConfig(BaseModel):
    auto_create_subnetworks: bool
    routing_mode: str = "REGIONAL"
    description: str | None = None
    mtu: int = Field(default=1460, ge=1300, le=8896)
    delete_default_routes_on_create: bool = False
    enable_ula_internal_ipv6: bool = False
    internal_ipv6_range: str | None = None
    network_firewall_policy_enforcement_order: str = "AFTER_CLASSIC_FIREWALL"
