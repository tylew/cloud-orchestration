"""Tests for secret management and code file MCP tools."""

import json
from unittest.mock import patch, MagicMock

import pytest


# ── Secret Tool Tests ────────────────────────────────────────


@patch("packages.mcp.tools.secrets.projects_store")
@patch("packages.mcp.tools.secrets.secrets_store")
def test_create_secret_calls_gcp_with_correct_project_id(mock_secrets_store, mock_projects_store):
    """create_secret calls store create_secret with correct gcp_project_id."""
    from packages.mcp.tools.secrets import create_secret

    mock_projects_store.get_project.return_value = {
        "id": "proj1",
        "environments": [{"name": "dev", "gcp_project_id": "test-gcp-project"}],
    }
    mock_projects_store.get_env_entry.return_value = {"gcp_project_id": "test-gcp-project"}
    mock_secrets_store.create_secret.return_value = {
        "secret_id": "my-secret", "version": "1", "status": "active",
    }

    result = create_secret("proj1", "dev", "my-secret", "super-secret-value")
    parsed = json.loads(result)

    mock_secrets_store.create_secret.assert_called_once()
    call_args = mock_secrets_store.create_secret.call_args
    # project_id arg (4th positional) should be gcp_project_id
    assert call_args[0][3] == "test-gcp-project"


@patch("packages.mcp.tools.secrets.projects_store")
@patch("packages.mcp.tools.secrets.secrets_store")
def test_create_secret_does_not_echo_value(mock_secrets_store, mock_projects_store):
    """create_secret response must NOT contain the secret value."""
    from packages.mcp.tools.secrets import create_secret

    mock_projects_store.get_project.return_value = {
        "id": "proj1",
        "environments": [{"name": "dev", "gcp_project_id": "test-gcp-project"}],
    }
    mock_projects_store.get_env_entry.return_value = {"gcp_project_id": "test-gcp-project"}
    mock_secrets_store.create_secret.return_value = {
        "secret_id": "my-secret", "version": "1", "status": "active",
    }

    result = create_secret("proj1", "dev", "my-secret", "super-secret-value")
    assert "super-secret-value" not in result


@patch("packages.mcp.tools.secrets.projects_store")
@patch("packages.mcp.tools.secrets.secrets_store")
def test_list_secrets_returns_formatted_list(mock_secrets_store, mock_projects_store):
    """list_secrets returns formatted list of secret names."""
    from packages.mcp.tools.secrets import list_secrets

    mock_secrets_store.list_secrets.return_value = [
        {"secret_id": "db-pass", "status": "active", "created_at": "2026-01-01"},
        {"secret_id": "api-key", "status": "active", "created_at": "2026-01-02"},
    ]

    result = list_secrets("proj1", "dev")
    parsed = json.loads(result)
    assert len(parsed["secrets"]) == 2
    assert parsed["secrets"][0]["secret_id"] == "db-pass"


@patch("packages.mcp.tools.secrets.projects_store")
@patch("packages.mcp.tools.secrets.secrets_store")
def test_get_secret_returns_name_and_value(mock_secrets_store, mock_projects_store):
    """get_secret returns secret name and value from Secret Manager."""
    from packages.mcp.tools.secrets import get_secret

    mock_projects_store.get_project.return_value = {
        "id": "proj1",
        "environments": [{"name": "dev", "gcp_project_id": "test-gcp-project"}],
    }
    mock_projects_store.get_env_entry.return_value = {"gcp_project_id": "test-gcp-project"}
    mock_secrets_store.get_secret.return_value = {"secret_id": "my-secret", "status": "active"}

    # Mock the GCP secret_manager.get_secret_value
    with patch("packages.mcp.tools.secrets.gcp_sm") as mock_gcp_sm:
        mock_gcp_sm.get_secret_value.return_value = "the-value"
        result = get_secret("proj1", "dev", "my-secret")
        parsed = json.loads(result)
        assert parsed["secret_id"] == "my-secret"
        assert parsed["value"] == "the-value"


@patch("packages.mcp.tools.secrets.projects_store")
@patch("packages.mcp.tools.secrets.secrets_store")
def test_delete_secret_calls_store_and_gcp(mock_secrets_store, mock_projects_store):
    """delete_secret calls both Firestore and GCP delete."""
    from packages.mcp.tools.secrets import delete_secret

    mock_projects_store.get_project.return_value = {
        "id": "proj1",
        "environments": [{"name": "dev", "gcp_project_id": "test-gcp-project"}],
    }
    mock_projects_store.get_env_entry.return_value = {"gcp_project_id": "test-gcp-project"}
    mock_secrets_store.delete_secret.return_value = {"secret_id": "my-secret", "status": "destroyed"}

    result = delete_secret("proj1", "dev", "my-secret")
    parsed = json.loads(result)
    assert parsed["status"] == "destroyed"
    mock_secrets_store.delete_secret.assert_called_once()


@patch("packages.mcp.tools.secrets.projects_store")
@patch("packages.mcp.tools.secrets.secrets_store")
def test_secret_tools_return_format_error_on_exception(mock_secrets_store, mock_projects_store):
    """Secret tools return format_error on exception."""
    from packages.mcp.tools.secrets import create_secret

    mock_projects_store.get_project.return_value = {
        "id": "proj1",
        "environments": [{"name": "dev", "gcp_project_id": "test-gcp-project"}],
    }
    mock_projects_store.get_env_entry.return_value = {"gcp_project_id": "test-gcp-project"}
    mock_secrets_store.create_secret.side_effect = Exception("GCP unavailable")

    result = create_secret("proj1", "dev", "my-secret", "value")
    parsed = json.loads(result)
    assert parsed["error_type"] == "create_secret_error"


# ── Code File Tool Tests ─────────────────────────────────────


@patch("packages.mcp.tools.code_files.code_storage")
def test_write_code_file_calls_gcs(mock_storage):
    """write_code_file calls GCS storage with correct path."""
    from packages.mcp.tools.code_files import write_code_file

    mock_storage.write_file.return_value = True
    result = write_code_file("proj1", "dev", "my-service", "main.py", "print('hi')")
    parsed = json.loads(result)
    assert parsed["status"] == "saved"
    mock_storage.write_file.assert_called_once_with("proj1", "dev", "my-service", "main.py", "print('hi')")


@patch("packages.mcp.tools.code_files.code_storage")
def test_read_code_file_returns_content(mock_storage):
    """read_code_file returns file content from GCS."""
    from packages.mcp.tools.code_files import read_code_file

    mock_storage.read_file.return_value = "print('hello')"
    result = read_code_file("proj1", "dev", "my-service", "main.py")
    parsed = json.loads(result)
    assert parsed["content"] == "print('hello')"


@patch("packages.mcp.tools.code_files.code_storage")
def test_list_code_files_returns_formatted_list(mock_storage):
    """list_code_files returns formatted file list."""
    from packages.mcp.tools.code_files import list_code_files

    mock_storage.list_files.return_value = ["main.py", "Dockerfile", "requirements.txt"]
    result = list_code_files("proj1", "dev", "my-service")
    parsed = json.loads(result)
    assert len(parsed["files"]) == 3


@patch("packages.mcp.tools.code_files.code_storage")
def test_delete_code_file_calls_gcs(mock_storage):
    """delete_code_file calls GCS delete."""
    from packages.mcp.tools.code_files import delete_code_file

    mock_storage.delete_file.return_value = True
    result = delete_code_file("proj1", "dev", "my-service", "main.py")
    parsed = json.loads(result)
    assert parsed["status"] == "deleted"
    mock_storage.delete_file.assert_called_once_with("proj1", "dev", "my-service", "main.py")


@patch("packages.mcp.tools.code_files.code_storage")
def test_code_file_tools_return_format_error_on_exception(mock_storage):
    """Code file tools return format_error on exception."""
    from packages.mcp.tools.code_files import write_code_file

    mock_storage.write_file.side_effect = Exception("GCS down")
    result = write_code_file("proj1", "dev", "my-service", "main.py", "content")
    parsed = json.loads(result)
    assert parsed["error_type"] == "write_code_file_error"
