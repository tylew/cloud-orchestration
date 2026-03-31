"""Abstract repository provider for compute node source code storage (per D-19)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class FileEntry:
    """A file in the repository."""
    path: str
    size: int
    updated_at: str  # ISO 8601


@dataclass
class Snapshot:
    """A point-in-time snapshot (Git tag) of a node's files."""
    id: str
    message: str
    user_email: str
    created_at: str  # ISO 8601
    file_count: int


class RepositoryProvider(ABC):
    """Abstraction over file storage for compute node source code (per D-19).

    Implementations handle Git operations behind the scenes. Users never
    interact with Git directly -- all operations are platform-managed.
    """

    @abstractmethod
    async def list_files(self, project_id: str, env: str, node: str) -> list[FileEntry]:
        """List all files for a compute node in the given environment."""
        ...

    @abstractmethod
    async def read_file(self, project_id: str, env: str, node: str, path: str) -> str | None:
        """Read a file's content. Returns None if not found."""
        ...

    @abstractmethod
    async def write_file(self, project_id: str, env: str, node: str, path: str, content: str) -> bool:
        """Create or update a file. Returns True on success."""
        ...

    @abstractmethod
    async def delete_file(self, project_id: str, env: str, node: str, path: str) -> bool:
        """Delete a file. Returns True on success."""
        ...

    @abstractmethod
    async def ensure_repo(self, project_id: str) -> str:
        """Ensure the repository exists for the project. Returns repo identifier."""
        ...

    @abstractmethod
    async def save_snapshot(self, project_id: str, env: str, node: str, message: str, user: str) -> str:
        """Create a snapshot (tag) of the current state. Returns snapshot ID."""
        ...

    @abstractmethod
    async def list_snapshots(self, project_id: str, env: str, node: str) -> list[Snapshot]:
        """List all snapshots for a compute node."""
        ...
