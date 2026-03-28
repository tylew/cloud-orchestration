"""Cloud DNS node type -- schema validation, registry, and template tests."""

import pytest
from packages.core.schemas.enums import NodeType
from packages.core.schemas.configs.cloud_dns import CloudDnsConfig, DnsRecord
from packages.core.schemas.configs import TYPE_TO_CONFIG
from packages.core.registry import REGISTRY
from packages.core.validation import REQUIRED_FIELDS


class TestCloudDnsConfig:
    def test_basic_zone(self):
        cfg = CloudDnsConfig(dns_name="example.com.")
        assert cfg.dns_name == "example.com."
        assert cfg.visibility == "public"
        assert cfg.records == []
        assert cfg.dnssec_enabled is False

    def test_private_zone(self):
        cfg = CloudDnsConfig(dns_name="internal.corp.", visibility="private")
        assert cfg.visibility == "private"

    def test_with_records(self):
        rec = DnsRecord(name="www", type="A", ttl=300, rrdatas=["1.2.3.4"])
        cfg = CloudDnsConfig(dns_name="example.com.", records=[rec])
        assert len(cfg.records) == 1
        assert cfg.records[0].type == "A"

    def test_mx_record(self):
        rec = DnsRecord(name="@", type="MX", rrdatas=["10 mail.example.com."])
        assert rec.rrdatas == ["10 mail.example.com."]

    def test_cross_node_ref_in_target(self):
        rec = DnsRecord(name="www", type="A", target="node:my-lb.ip_address")
        assert rec.target == "node:my-lb.ip_address"

    def test_labels(self):
        cfg = CloudDnsConfig(dns_name="example.com.", labels={"env": "prod"})
        assert cfg.labels == {"env": "prod"}

    def test_force_destroy(self):
        cfg = CloudDnsConfig(dns_name="example.com.", force_destroy=True)
        assert cfg.force_destroy is True


class TestCloudDnsRegistration:
    def test_enum_value(self):
        assert NodeType.CLOUD_DNS.value == "cloud_dns"

    def test_type_to_config(self):
        assert TYPE_TO_CONFIG[NodeType.CLOUD_DNS] is CloudDnsConfig

    def test_registry_entry(self):
        defn = REGISTRY[NodeType.CLOUD_DNS]
        assert defn.category == "Network"
        assert defn.is_compute is False
        assert defn.terraform_resource == "google_dns_managed_zone"
        assert defn.iam_scope is None

    def test_registry_default_outputs(self):
        defn = REGISTRY[NodeType.CLOUD_DNS]
        output_names = {o["name"] for o in defn.default_outputs}
        assert "name_servers" in output_names
        assert "dns_name" in output_names

    def test_required_fields(self):
        reqs = REQUIRED_FIELDS["cloud_dns"]
        field_paths = [r.field_path for r in reqs]
        assert "dns_name" in field_paths
