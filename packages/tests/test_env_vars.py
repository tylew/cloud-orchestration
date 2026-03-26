"""Tests for the unified EnvVarEntry model."""

import pytest
from pydantic import ValidationError


class TestEnvVarEntry:
    def test_value_type_valid(self):
        from packages.core.schemas.configs.env_vars import EnvVarEntry
        entry = EnvVarEntry(name="LOG_LEVEL", type="value", value="debug")
        assert entry.name == "LOG_LEVEL"
        assert entry.type == "value"
        assert entry.value == "debug"
        assert entry.secret is None

    def test_secret_type_valid(self):
        from packages.core.schemas.configs.env_vars import EnvVarEntry
        entry = EnvVarEntry(name="DB_URL", type="secret", secret="db-url")
        assert entry.name == "DB_URL"
        assert entry.type == "secret"
        assert entry.secret == "db-url"
        assert entry.version == "latest"
        assert entry.value is None

    def test_secret_type_with_version(self):
        from packages.core.schemas.configs.env_vars import EnvVarEntry
        entry = EnvVarEntry(name="DB_URL", type="secret", secret="db-url", version="3")
        assert entry.version == "3"

    def test_value_type_rejects_secret_field(self):
        from packages.core.schemas.configs.env_vars import EnvVarEntry
        with pytest.raises(ValidationError, match="must not set 'secret'"):
            EnvVarEntry(name="X", type="value", value="y", secret="bad")

    def test_secret_type_rejects_value_field(self):
        from packages.core.schemas.configs.env_vars import EnvVarEntry
        with pytest.raises(ValidationError, match="must not set 'value'"):
            EnvVarEntry(name="X", type="secret", secret="s", value="bad")

    def test_value_type_allows_none_value(self):
        from packages.core.schemas.configs.env_vars import EnvVarEntry
        entry = EnvVarEntry(name="EMPTY", type="value")
        assert entry.value is None

    def test_secret_type_allows_none_secret(self):
        from packages.core.schemas.configs.env_vars import EnvVarEntry
        entry = EnvVarEntry(name="EMPTY", type="secret")
        assert entry.secret is None


class TestCloudRunConfigEnvVars:
    def test_cloud_run_config_accepts_env_vars(self):
        from packages.core.schemas.configs.cloud_run import CloudRunConfig
        config = CloudRunConfig(
            image="gcr.io/test/image:latest",
            env_vars=[
                {"name": "LOG_LEVEL", "type": "value", "value": "debug"},
                {"name": "DB_URL", "type": "secret", "secret": "db-url"},
            ],
        )
        assert len(config.env_vars) == 2
        assert config.env_vars[0].type == "value"
        assert config.env_vars[1].type == "secret"

    def test_cloud_run_config_no_env_field(self):
        from packages.core.schemas.configs.cloud_run import CloudRunConfig
        assert "env" not in CloudRunConfig.model_fields

    def test_cloud_run_config_no_secrets_field(self):
        from packages.core.schemas.configs.cloud_run import CloudRunConfig
        assert "secrets" not in CloudRunConfig.model_fields


class TestCloudRunJobConfigEnvVars:
    def test_job_config_accepts_env_vars(self):
        from packages.core.schemas.configs.cloud_run_job import CloudRunJobConfig
        config = CloudRunJobConfig(
            image="gcr.io/test/image:latest",
            env_vars=[
                {"name": "BATCH_SIZE", "type": "value", "value": "100"},
            ],
        )
        assert len(config.env_vars) == 1

    def test_job_config_no_legacy_fields(self):
        from packages.core.schemas.configs.cloud_run_job import CloudRunJobConfig
        assert "env" not in CloudRunJobConfig.model_fields
        assert "secrets" not in CloudRunJobConfig.model_fields


class TestCloudFunctionConfigEnvVars:
    def test_function_config_accepts_env_vars(self):
        from packages.core.schemas.configs.cloud_function import CloudFunctionConfig
        config = CloudFunctionConfig(
            runtime="python312",
            entry_point="main",
            env_vars=[
                {"name": "API_KEY", "type": "secret", "secret": "api-key"},
            ],
        )
        assert len(config.env_vars) == 1
        assert config.env_vars[0].type == "secret"

    def test_function_config_no_legacy_fields(self):
        from packages.core.schemas.configs.cloud_function import CloudFunctionConfig
        assert "env" not in CloudFunctionConfig.model_fields
        assert "secrets" not in CloudFunctionConfig.model_fields
        assert "secret_environment_variables" not in CloudFunctionConfig.model_fields
