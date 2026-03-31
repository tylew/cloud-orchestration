"""Cloud DNS node type -- schema validation, registry, and template tests."""

import os
import pytest
from jinja2 import Environment, FileSystemLoader
from core.schemas.enums import NodeType
from core.schemas.configs.cloud_dns import CloudDnsConfig, DnsRecord
from core.schemas.configs import TYPE_TO_CONFIG
from core.registry import REGISTRY
from core.validation import REQUIRED_FIELDS


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


class TestCloudDnsTerraform:
    @pytest.fixture
    def env(self):
        tmpl_dir = os.path.join(os.path.dirname(__file__), "..", "core", "terraform", "templates")
        return Environment(loader=FileSystemLoader(tmpl_dir), trim_blocks=True, lstrip_blocks=True)

    @pytest.fixture
    def base_context(self):
        """Minimal render context mimicking generator.py's template call."""
        class FakeNode:
            name = "my-dns"
        class FakeGlobal:
            project_id = "test-project"
            region = "us-central1"
        class FakeDefn:
            terraform_resource = "google_dns_managed_zone"
        return {
            "node": FakeNode(),
            "global_": FakeGlobal(),
            "defn": FakeDefn(),
            "api_depends_on": [],
            "resolve_ref": lambda ref: 'google_compute_global_address.my-lb.address',
        }

    def test_managed_zone_basic(self, env, base_context):
        cfg = CloudDnsConfig(dns_name="example.com.", description="Test zone")
        base_context["config"] = cfg
        tmpl = env.get_template("cloud_dns.tf.j2")
        result = tmpl.render(**base_context)
        assert 'google_dns_managed_zone' in result
        assert '"my-dns"' in result
        assert 'example.com.' in result

    def test_trailing_dot_added(self, env, base_context):
        cfg = CloudDnsConfig(dns_name="example.com")  # No trailing dot
        base_context["config"] = cfg
        tmpl = env.get_template("cloud_dns.tf.j2")
        result = tmpl.render(**base_context)
        assert 'example.com.' in result

    def test_record_set_a_record(self, env, base_context):
        rec = DnsRecord(name="www", type="A", ttl=300, rrdatas=["1.2.3.4"])
        cfg = CloudDnsConfig(dns_name="example.com.", records=[rec])
        base_context["config"] = cfg
        tmpl = env.get_template("cloud_dns.tf.j2")
        result = tmpl.render(**base_context)
        assert 'google_dns_record_set' in result
        assert '"A"' in result
        assert '300' in result
        assert '1.2.3.4' in result

    def test_apex_record(self, env, base_context):
        rec = DnsRecord(name="@", type="A", rrdatas=["1.2.3.4"])
        cfg = CloudDnsConfig(dns_name="example.com.", records=[rec])
        base_context["config"] = cfg
        tmpl = env.get_template("cloud_dns.tf.j2")
        result = tmpl.render(**base_context)
        # Apex record name should reference zone dns_name directly
        assert 'google_dns_managed_zone.my-dns.dns_name' in result

    def test_cross_node_ref(self, env, base_context):
        rec = DnsRecord(name="www", type="A", target="node:my-lb.ip_address")
        cfg = CloudDnsConfig(dns_name="example.com.", records=[rec])
        base_context["config"] = cfg
        tmpl = env.get_template("cloud_dns.tf.j2")
        result = tmpl.render(**base_context)
        assert 'google_compute_global_address.my-lb.address' in result

    def test_dnssec_enabled(self, env, base_context):
        cfg = CloudDnsConfig(dns_name="example.com.", dnssec_enabled=True)
        base_context["config"] = cfg
        tmpl = env.get_template("cloud_dns.tf.j2")
        result = tmpl.render(**base_context)
        assert 'dnssec_config' in result
        assert '"on"' in result

    def test_labels(self, env, base_context):
        cfg = CloudDnsConfig(dns_name="example.com.", labels={"env": "prod"})
        base_context["config"] = cfg
        tmpl = env.get_template("cloud_dns.tf.j2")
        result = tmpl.render(**base_context)
        assert '"env"' in result
        assert '"prod"' in result

    def test_force_destroy(self, env, base_context):
        cfg = CloudDnsConfig(dns_name="example.com.", force_destroy=True)
        base_context["config"] = cfg
        tmpl = env.get_template("cloud_dns.tf.j2")
        result = tmpl.render(**base_context)
        assert 'force_destroy = true' in result

    def test_private_visibility_config(self, env, base_context):
        cfg = CloudDnsConfig(
            dns_name="internal.corp.",
            visibility="private",
            networks=["google_compute_network.my-vpc.id"],
        )
        base_context["config"] = cfg
        tmpl = env.get_template("cloud_dns.tf.j2")
        result = tmpl.render(**base_context)
        assert 'private_visibility_config' in result
        assert 'network_url' in result
        assert 'google_compute_network.my-vpc.id' in result
