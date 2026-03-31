"""Tests for blueprint promotion env var stripping."""

from packages.platform.store.blueprints import _strip_env_var_values


class TestStripEnvVarValues:
    def test_strips_value_entries(self):
        nodes = [
            {
                "name": "my-svc", "type": "cloud_run", "slug": "my-svc",
                "config": {
                    "image": "gcr.io/test/img",
                    "env_vars": [
                        {"name": "LOG_LEVEL", "type": "value", "value": "debug"},
                        {"name": "PORT", "type": "value", "value": "8080"},
                    ],
                },
            },
        ]
        result = _strip_env_var_values(nodes)
        env_vars = result[0]["config"]["env_vars"]
        assert len(env_vars) == 2
        assert env_vars[0]["name"] == "LOG_LEVEL"
        assert env_vars[0]["type"] == "value"
        assert env_vars[0].get("value") is None
        assert env_vars[1].get("value") is None

    def test_strips_secret_entries(self):
        nodes = [
            {
                "name": "my-svc", "type": "cloud_run", "slug": "my-svc",
                "config": {
                    "image": "gcr.io/test/img",
                    "env_vars": [
                        {"name": "DB_URL", "type": "secret", "secret": "db-url", "version": "3"},
                    ],
                },
            },
        ]
        result = _strip_env_var_values(nodes)
        env_vars = result[0]["config"]["env_vars"]
        assert env_vars[0]["name"] == "DB_URL"
        assert env_vars[0]["type"] == "secret"
        assert env_vars[0].get("secret") is None
        assert env_vars[0]["version"] == "latest"

    def test_non_compute_nodes_unchanged(self):
        nodes = [
            {
                "name": "my-vpc", "type": "vpc", "slug": "my-vpc",
                "config": {"auto_create_subnetworks": False},
            },
        ]
        result = _strip_env_var_values(nodes)
        assert result[0]["config"]["auto_create_subnetworks"] is False

    def test_mixed_nodes(self):
        nodes = [
            {"name": "my-vpc", "type": "vpc", "slug": "my-vpc", "config": {}},
            {
                "name": "my-func", "type": "cloud_function", "slug": "my-func",
                "config": {
                    "runtime": "python312",
                    "entry_point": "main",
                    "env_vars": [
                        {"name": "API_KEY", "type": "secret", "secret": "key"},
                    ],
                },
            },
        ]
        result = _strip_env_var_values(nodes)
        assert "env_vars" not in result[0]["config"]
        assert result[1]["config"]["env_vars"][0].get("secret") is None

    def test_does_not_mutate_original(self):
        nodes = [
            {
                "name": "my-svc", "type": "cloud_run", "slug": "my-svc",
                "config": {
                    "env_vars": [
                        {"name": "X", "type": "value", "value": "original"},
                    ],
                },
            },
        ]
        _strip_env_var_values(nodes)
        assert nodes[0]["config"]["env_vars"][0]["value"] == "original"
