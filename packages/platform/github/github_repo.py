"""GitHub-backed RepositoryProvider using GitHub App installation tokens (per D-15, D-18)."""

import base64
import logging
import os
import time
from datetime import datetime, timezone, timedelta

import httpx
import jwt

from packages.platform.github.repository import RepositoryProvider, FileEntry, Snapshot

log = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


class GitHubRepositoryProvider(RepositoryProvider):
    """Repository provider backed by GitHub REST API via a GitHub App.

    One repo per project (per D-15). File paths: {node}/{path}.
    Branch names map 1:1 to environments (per D-21).
    """

    def __init__(
        self,
        app_id: str,
        private_key: str,
        installation_id: str,
        org: str | None = None,
    ):
        self._app_id = app_id
        self._private_key = private_key
        self._installation_id = installation_id
        self._org = org or os.environ.get("GITHUB_ORG", "pl4m-platform")
        self._token: str | None = None
        self._token_expires: datetime | None = None
        self._client = httpx.AsyncClient(timeout=30.0)

    # --- Authentication -------------------------------------------------------

    def _generate_jwt(self) -> str:
        """Generate a JWT signed with the GitHub App's private key."""
        now = int(time.time())
        payload = {
            "iat": now - 60,  # issued at (60s clock drift allowance)
            "exp": now + (10 * 60),  # 10 min expiry (GitHub max)
            "iss": self._app_id,
        }
        return jwt.encode(payload, self._private_key, algorithm="RS256")

    async def _get_installation_token(self) -> str:
        """Get an installation access token, using cache if valid."""
        if self._token and self._token_expires and datetime.now(timezone.utc) < self._token_expires:
            return self._token

        app_jwt = self._generate_jwt()
        resp = await self._client.post(
            f"{GITHUB_API}/app/installations/{self._installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data["token"]
        # Tokens expire in 1 hour; refresh 5 min early
        self._token_expires = datetime.now(timezone.utc) + timedelta(minutes=55)
        return self._token

    async def _authed_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make an authenticated request to GitHub API."""
        token = await self._get_installation_token()
        headers = kwargs.pop("headers", {})
        headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
        })
        return await self._client.request(method, url, headers=headers, **kwargs)

    # --- Repo helpers ---------------------------------------------------------

    def _repo_url(self, project_id: str) -> str:
        """Build the API URL for a project repo."""
        return f"{GITHUB_API}/repos/{self._org}/{project_id}"

    def _contents_url(self, project_id: str, file_path: str) -> str:
        """Build the API URL for a file in the repo."""
        return f"{self._repo_url(project_id)}/contents/{file_path}"

    async def _ensure_branch(self, project_id: str, branch: str) -> None:
        """Ensure a branch exists. If not, create it from the default branch."""
        url = f"{self._repo_url(project_id)}/branches/{branch}"
        resp = await self._authed_request("GET", url)
        if resp.status_code == 200:
            return

        # Get default branch SHA
        repo_resp = await self._authed_request("GET", self._repo_url(project_id))
        if repo_resp.status_code != 200:
            log.error("Failed to get repo info for branch creation: %s", repo_resp.status_code)
            return
        default_branch = repo_resp.json().get("default_branch", "main")

        ref_resp = await self._authed_request(
            "GET",
            f"{self._repo_url(project_id)}/git/ref/heads/{default_branch}",
        )
        if ref_resp.status_code != 200:
            log.error("Failed to get default branch ref: %s", ref_resp.status_code)
            return
        sha = ref_resp.json()["object"]["sha"]

        # Create the branch
        create_resp = await self._authed_request(
            "POST",
            f"{self._repo_url(project_id)}/git/refs",
            json={"ref": f"refs/heads/{branch}", "sha": sha},
        )
        if create_resp.status_code in (200, 201):
            log.info("Created branch %s for project %s", branch, project_id)
        else:
            log.warning("Branch creation returned %s: %s", create_resp.status_code, create_resp.text)

    # --- RepositoryProvider interface -----------------------------------------

    async def ensure_repo(self, project_id: str) -> str:
        """Create a private repo for the project. Idempotent (422 = already exists)."""
        url = f"{GITHUB_API}/orgs/{self._org}/repos"
        resp = await self._authed_request(
            "POST",
            url,
            json={
                "name": project_id,
                "private": True,
                "auto_init": True,
            },
        )
        full_name = f"{self._org}/{project_id}"
        if resp.status_code == 201:
            full_name = resp.json().get("full_name", full_name)
            log.info("Created repo %s", full_name)
        elif resp.status_code == 422:
            log.info("Repo %s already exists", full_name)
        else:
            log.error("Failed to create repo: %s %s", resp.status_code, resp.text)
        return full_name

    async def list_files(self, project_id: str, env: str, node: str) -> list[FileEntry]:
        """List files under {node}/ directory on the env branch."""
        await self._ensure_branch(project_id, env)
        url = self._contents_url(project_id, node)
        resp = await self._authed_request("GET", url, params={"ref": env})

        if resp.status_code == 404:
            return []
        if resp.status_code != 200:
            log.error("list_files failed: %s", resp.status_code)
            return []

        items = resp.json()
        if not isinstance(items, list):
            return []

        return [
            FileEntry(
                path=item["name"],
                size=item.get("size", 0),
                updated_at="",  # Contents API doesn't return timestamps
            )
            for item in items
            if item.get("type") == "file"
        ]

    async def read_file(self, project_id: str, env: str, node: str, path: str) -> str | None:
        """Read a file from {node}/{path} on the env branch."""
        url = self._contents_url(project_id, f"{node}/{path}")
        resp = await self._authed_request("GET", url, params={"ref": env})

        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            log.error("read_file failed: %s", resp.status_code)
            return None

        data = resp.json()
        content_b64 = data.get("content", "")
        # GitHub returns base64 with newlines
        return base64.b64decode(content_b64).decode("utf-8")

    async def write_file(self, project_id: str, env: str, node: str, path: str, content: str) -> bool:
        """Create or update a file at {node}/{path} on the env branch."""
        await self._ensure_branch(project_id, env)
        file_path = f"{node}/{path}"
        url = self._contents_url(project_id, file_path)

        # Check if file exists (need SHA for updates)
        existing_sha = None
        get_resp = await self._authed_request("GET", url, params={"ref": env})
        if get_resp.status_code == 200:
            existing_sha = get_resp.json().get("sha")

        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        body: dict = {
            "message": f"Update {path}",
            "content": encoded,
            "branch": env,
        }
        if existing_sha:
            body["sha"] = existing_sha

        put_resp = await self._authed_request("PUT", url, json=body)
        if put_resp.status_code in (200, 201):
            return True
        log.error("write_file failed: %s %s", put_resp.status_code, put_resp.text)
        return False

    async def delete_file(self, project_id: str, env: str, node: str, path: str) -> bool:
        """Delete a file at {node}/{path} on the env branch."""
        file_path = f"{node}/{path}"
        url = self._contents_url(project_id, file_path)

        # Get current SHA
        get_resp = await self._authed_request("GET", url, params={"ref": env})
        if get_resp.status_code != 200:
            return False
        sha = get_resp.json().get("sha")
        if not sha:
            return False

        del_resp = await self._authed_request(
            "DELETE",
            url,
            json={"message": f"Delete {path}", "sha": sha, "branch": env},
        )
        return del_resp.status_code == 200

    async def save_snapshot(self, project_id: str, env: str, node: str, message: str, user: str) -> str:
        """Create a Git tag as a snapshot marker."""
        # Get current HEAD of the env branch
        ref_resp = await self._authed_request(
            "GET",
            f"{self._repo_url(project_id)}/git/ref/heads/{env}",
        )
        if ref_resp.status_code != 200:
            log.error("Cannot get branch HEAD for snapshot: %s", ref_resp.status_code)
            return ""

        sha = ref_resp.json()["object"]["sha"]
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        tag_name = f"snapshot-{node}-{timestamp}"

        tag_resp = await self._authed_request(
            "POST",
            f"{self._repo_url(project_id)}/git/tags",
            json={
                "tag": tag_name,
                "message": f"{message} (by {user})",
                "object": sha,
                "type": "commit",
                "tagger": {
                    "name": user,
                    "email": user,
                    "date": datetime.now(timezone.utc).isoformat(),
                },
            },
        )
        if tag_resp.status_code != 201:
            log.error("Failed to create tag: %s", tag_resp.status_code)
            return ""

        # Create the ref for the tag
        ref_create = await self._authed_request(
            "POST",
            f"{self._repo_url(project_id)}/git/refs",
            json={"ref": f"refs/tags/{tag_name}", "sha": tag_resp.json()["sha"]},
        )
        if ref_create.status_code not in (200, 201):
            log.warning("Tag ref creation failed: %s", ref_create.status_code)

        return tag_name

    async def list_snapshots(self, project_id: str, env: str, node: str) -> list[Snapshot]:
        """List snapshots (tags) for a specific node."""
        prefix = f"snapshot-{node}-"
        resp = await self._authed_request(
            "GET",
            f"{self._repo_url(project_id)}/git/matching-refs/tags/{prefix}",
        )
        if resp.status_code != 200:
            return []

        snapshots = []
        for ref in resp.json():
            tag_name = ref["ref"].replace("refs/tags/", "")
            # Fetch tag details
            tag_resp = await self._authed_request("GET", ref["object"]["url"])
            if tag_resp.status_code == 200:
                tag_data = tag_resp.json()
                snapshots.append(Snapshot(
                    id=tag_name,
                    message=tag_data.get("message", ""),
                    user_email=tag_data.get("tagger", {}).get("email", ""),
                    created_at=tag_data.get("tagger", {}).get("date", ""),
                    file_count=0,  # Not available from tag metadata
                ))
        return snapshots
