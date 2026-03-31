from pydantic import BaseModel


class SecondaryIpRange(BaseModel):
    range_name: str
    ip_cidr_range: str


class SubnetLogConfig(BaseModel):
    aggregation_interval: str | None = None
    flow_sampling: float | None = None
    metadata: str | None = None
    metadata_fields: list[str] = []
    filter_expr: str | None = None


class SubnetConfig(BaseModel):
    ip_cidr_range: str
    region: str
    network: str
    description: str | None = None
    private_ip_google_access: bool = True
    private_ipv6_google_access: str | None = None
    secondary_ip_ranges: list[SecondaryIpRange] | None = None
    log_config: SubnetLogConfig | None = None
    purpose: str = "PRIVATE"
    role: str | None = None  # ACTIVE | BACKUP — for REGIONAL_MANAGED_PROXY subnets
    stack_type: str = "IPV4_ONLY"
    ipv6_access_type: str | None = None  # EXTERNAL | INTERNAL
