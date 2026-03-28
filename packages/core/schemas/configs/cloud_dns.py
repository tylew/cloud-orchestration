"""Cloud DNS managed zone configuration."""

from pydantic import BaseModel
from typing import Literal


class DnsRecord(BaseModel):
    """A single DNS record entry within a Cloud DNS zone.

    Note: MX priority is embedded in the rrdatas strings per TF convention,
    e.g. rrdatas=["10 mail.example.com."] -- there is no separate priority field.
    """
    name: str = "@"
    type: Literal["A", "AAAA", "CNAME", "MX", "TXT", "NS", "SRV", "PTR", "SOA", "CAA"] = "A"
    ttl: int = 300
    rrdatas: list[str] = []
    target: str | None = None


class CloudDnsConfig(BaseModel):
    """Configuration for a Cloud DNS managed zone."""
    dns_name: str = ""
    visibility: Literal["public", "private"] = "public"
    description: str = ""
    dnssec_enabled: bool = False
    force_destroy: bool = False
    records: list[DnsRecord] = []
    networks: list[str] = []
    labels: dict[str, str] = {}
