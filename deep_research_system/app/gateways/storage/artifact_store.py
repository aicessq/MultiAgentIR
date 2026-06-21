"""ArtifactStore - unified storage for research artifacts.

Key responsibilities:
1. Store artifacts (plans, analyses, reports, etc.)
2. Retrieve artifacts by ID
3. Track revision history
4. Support different storage backends (file, object storage, database)

Key constraints:
- Artifacts are immutable once stored
- Revision chain must be tracked
- Large artifacts stored in object storage, metadata in database
- Content hash for integrity verification
"""

from __future__ import annotations

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel

from app.domain.enums import ArtifactType
from app.domain.models import Artifact, RevisionMeta

logger = logging.getLogger(__name__)


class ArtifactStore(ABC):
    """Abstract base class for artifact storage."""

    @abstractmethod
    async def store(self, artifact: Artifact, content: str | dict | bytes) -> str:
        """Store an artifact and return its storage URI."""
        pass

    @abstractmethod
    async def retrieve(self, artifact_id: str) -> tuple[Artifact, str | dict | bytes]:
        """Retrieve an artifact by ID."""
        pass

    @abstractmethod
    async def get_revision_chain(self, artifact_id: str) -> list[RevisionMeta]:
        """Get the revision history for an artifact."""
        pass

    @abstractmethod
    async def get_latest_revision(self, run_id: str, artifact_type: ArtifactType) -> Artifact | None:
        """Get the latest revision of a specific artifact type for a run."""
        pass

    @abstractmethod
    async def exists(self, artifact_id: str) -> bool:
        """Check if an artifact exists."""
        pass


class InMemoryArtifactStore(ArtifactStore):
    """In-memory artifact store for testing."""

    def __init__(self) -> None:
        self._artifacts: dict[str, Artifact] = {}
        self._contents: dict[str, str | dict | bytes] = {}
        self._by_run_type: dict[str, dict[ArtifactType, list[str]]] = {}

    async def store(self, artifact: Artifact, content: str | dict | bytes) -> str:
        """Store an artifact."""
        artifact_id = artifact.artifact_id
        self._artifacts[artifact_id] = artifact
        self._contents[artifact_id] = content

        # Index by run_id and type
        run_key = artifact.run_id
        if run_key not in self._by_run_type:
            self._by_run_type[run_key] = {}
        if artifact.artifact_type not in self._by_run_type[run_key]:
            self._by_run_type[run_key][artifact.artifact_type] = []
        self._by_run_type[run_key][artifact.artifact_type].append(artifact_id)

        return f"memory://{artifact_id}"

    async def retrieve(self, artifact_id: str) -> tuple[Artifact, str | dict | bytes]:
        """Retrieve an artifact."""
        if artifact_id not in self._artifacts:
            raise KeyError(f"Artifact not found: {artifact_id}")
        return self._artifacts[artifact_id], self._contents[artifact_id]

    async def get_revision_chain(self, artifact_id: str) -> list[RevisionMeta]:
        """Get revision history."""
        if artifact_id not in self._artifacts:
            return []

        artifact = self._artifacts[artifact_id]
        chain = [artifact.revision]

        # Walk backwards through supersedes chain
        current = artifact.revision.supersedes_revision_id
        while current:
            # Find artifact with this revision_id
            for aid, a in self._artifacts.items():
                if a.revision.revision_id == current:
                    chain.append(a.revision)
                    current = a.revision.supersedes_revision_id
                    break
            else:
                break

        return list(reversed(chain))

    async def get_latest_revision(self, run_id: str, artifact_type: ArtifactType) -> Artifact | None:
        """Get latest revision."""
        run_key = run_id
        if run_key not in self._by_run_type:
            return None
        if artifact_type not in self._by_run_type[run_key]:
            return None

        ids = self._by_run_type[run_key][artifact_type]
        if not ids:
            return None

        # Find the one with highest revision_number
        latest = None
        latest_num = -1
        for aid in ids:
            artifact = self._artifacts[aid]
            if artifact.revision.revision_number > latest_num:
                latest = artifact
                latest_num = artifact.revision.revision_number

        return latest

    async def exists(self, artifact_id: str) -> bool:
        """Check if artifact exists."""
        return artifact_id in self._artifacts

    def get_all_artifacts(self) -> dict[str, Artifact]:
        """Get all stored artifacts."""
        return self._artifacts


class FileArtifactStore(ArtifactStore):
    """File-based artifact store for development."""

    def __init__(self, base_path: str = "./artifacts") -> None:
        self._base_path = base_path
        self._metadata_cache: dict[str, Artifact] = {}

    async def store(self, artifact: Artifact, content: str | dict | bytes) -> str:
        """Store an artifact to file."""
        import os

        artifact_id = artifact.artifact_id
        artifact_type = artifact.artifact_type.value
        run_id = artifact.run_id

        # Create directory structure
        dir_path = os.path.join(self._base_path, run_id, artifact_type)
        os.makedirs(dir_path, exist_ok=True)

        # Determine file extension and path
        if isinstance(content, dict):
            file_ext = ".json"
            file_content = json.dumps(content, indent=2)
        elif isinstance(content, bytes):
            file_ext = ".bin"
            file_content = content
        else:
            file_ext = ".txt"
            file_content = content

        file_path = os.path.join(dir_path, f"{artifact_id}{file_ext}")

        # Write content
        with open(file_path, "wb") as f:
            if isinstance(file_content, str):
                f.write(file_content.encode("utf-8"))
            else:
                f.write(file_content)

        # Write metadata
        meta_path = os.path.join(dir_path, f"{artifact_id}.meta.json")
        with open(meta_path, "w") as f:
            json.dump(artifact.model_dump(mode="json"), f, indent=2)

        self._metadata_cache[artifact_id] = artifact

        return file_path

    async def retrieve(self, artifact_id: str) -> tuple[Artifact, str | dict | bytes]:
        """Retrieve an artifact from file."""
        import os

        if artifact_id in self._metadata_cache:
            artifact = self._metadata_cache[artifact_id]
        else:
            # Find metadata file
            for root, dirs, files in os.walk(self._base_path):
                for f in files:
                    if f == f"{artifact_id}.meta.json":
                        meta_path = os.path.join(root, f)
                        with open(meta_path) as mf:
                            data = json.load(mf)
                        artifact = Artifact.model_validate(data)
                        self._metadata_cache[artifact_id] = artifact
                        break

        if artifact_id not in self._metadata_cache:
            raise KeyError(f"Artifact not found: {artifact_id}")

        artifact = self._metadata_cache[artifact_id]

        # Find content file
        for root, dirs, files in os.walk(self._base_path):
            for f in files:
                if f.startswith(artifact_id) and not f.endswith(".meta.json"):
                    file_path = os.path.join(root, f)
                    with open(file_path, "rb") as cf:
                        content = cf.read()

                    if f.endswith(".json"):
                        content = json.loads(content)
                    elif f.endswith(".txt"):
                        content = content.decode("utf-8")

                    return artifact, content

        raise KeyError(f"Content not found for artifact: {artifact_id}")

    async def get_revision_chain(self, artifact_id: str) -> list[RevisionMeta]:
        """Get revision history."""
        # Simplified - would need to scan all metadata files
        if artifact_id not in self._metadata_cache:
            return []
        return [self._metadata_cache[artifact_id].revision]

    async def get_latest_revision(self, run_id: str, artifact_type: ArtifactType) -> Artifact | None:
        """Get latest revision."""
        import os

        dir_path = os.path.join(self._base_path, run_id, artifact_type.value)
        if not os.path.exists(dir_path):
            return None

        latest = None
        latest_num = -1

        for f in os.listdir(dir_path):
            if f.endswith(".meta.json"):
                meta_path = os.path.join(dir_path, f)
                with open(meta_path) as mf:
                    data = json.load(mf)
                artifact = Artifact.model_validate(data)
                if artifact.revision.revision_number > latest_num:
                    latest = artifact
                    latest_num = artifact.revision.revision_number

        return latest

    async def exists(self, artifact_id: str) -> bool:
        """Check if artifact exists."""
        import os

        if artifact_id in self._metadata_cache:
            return True

        for root, dirs, files in os.walk(self._base_path):
            for f in files:
                if f == f"{artifact_id}.meta.json":
                    return True

        return False