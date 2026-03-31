"""Unit tests for per-env project store helpers."""


class TestGetEnvEntry:
    def test_finds_env_by_name(self):
        from packages.platform.store.projects import get_env_entry
        envs = [
            {"id": "1", "name": "dev", "gcp_project_id": "proj-dev"},
            {"id": "2", "name": "staging", "gcp_project_id": "proj-staging"},
        ]
        entry = get_env_entry(envs, "staging")
        assert entry["gcp_project_id"] == "proj-staging"

    def test_returns_none_for_missing_env(self):
        from packages.platform.store.projects import get_env_entry
        envs = [{"id": "1", "name": "dev"}]
        assert get_env_entry(envs, "prod") is None

    def test_returns_none_for_empty_list(self):
        from packages.platform.store.projects import get_env_entry
        assert get_env_entry([], "dev") is None
