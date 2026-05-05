from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time


class JobStatus(str):
    PENDING = "pending"
    PROCESSING = "processing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ArtifactJob:
    job_id: str
    artifact_type: str
    source_id: str
    source_path: str
    content: Optional[bytes] = None
    status: str = JobStatus.PENDING
    chunks: List[Dict[str, Any]] = field(default_factory=list)
    embedded_chunks: List[Dict[str, Any]] = field(default_factory=list)
    total_chunks: int = 0
    indexed_count: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def progress(self) -> float:
        if self.status == JobStatus.COMPLETED:
            return 1.0
        elif self.status == JobStatus.FAILED:
            return 0.0
        elif self.status == JobStatus.PENDING:
            return 0.0
        elif self.status == JobStatus.PROCESSING:
            return 0.1
        elif self.status == JobStatus.CHUNKING:
            return 0.3
        elif self.status == JobStatus.EMBEDDING:
            return 0.6
        elif self.status == JobStatus.INDEXING:
            return 0.9
        return 0.0