"""
Memory System - Three-tier memory architecture.

Provides:
- Short-term: Conversation context within session
- Project: Project-specific context across sessions
- Long-term: Persistent knowledge across projects
"""

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
import logging

logger = logging.getLogger(__name__)


class MemoryTier(str, Enum):
    SHORT_TERM = "short_term"
    PROJECT = "project"
    LONG_TERM = "long_term"


class MemoryScope(str, Enum):
    SESSION = "session"
    PROJECT = "project"
    GLOBAL = "global"


@dataclass
class MemoryEntry:
    entry_id: str
    tier: str
    scope: str
    key: str
    value: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    access_count: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None


@dataclass
class ReasoningTrace:
    step: str
    thinking: str
    evidence: List[str] = field(default_factory=list)
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)


class ShortTermMemory:
    def __init__(self, max_entries: int = 100, ttl_seconds: int = 3600):
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._entries: Dict[str, MemoryEntry] = {}
        self._reasoning_trace: List[ReasoningTrace] = []

    def store(self, key: str, value: Any, metadata: Optional[Dict] = None) -> str:
        entry_id = f"stm_{key}_{int(time.time() * 1000)}"

        if len(self._entries) >= self.max_entries:
            self._evict_oldest()

        self._entries[entry_id] = MemoryEntry(
            entry_id=entry_id,
            tier=MemoryTier.SHORT_TERM.value,
            scope=MemoryScope.SESSION.value,
            key=key,
            value=value,
            metadata=metadata or {},
            expires_at=time.time() + self.ttl_seconds,
        )
        return entry_id

    def retrieve(self, key: str) -> Optional[Any]:
        for entry in self._entries.values():
            if entry.key == key:
                if self._is_expired(entry):
                    self._entries.pop(entry.entry_id, None)
                    return None
                entry.access_count += 1
                entry.updated_at = time.time()
                return entry.value
        return None

    def retrieve_recent(self, limit: int = 10) -> List[MemoryEntry]:
        self._cleanupExpired()
        sorted_entries = sorted(
            self._entries.values(), key=lambda e: e.updated_at, reverse=True
        )
        return sorted_entries[:limit]

    def add_reasoning_trace(
        self,
        step: str,
        thinking: str,
        evidence: Optional[List[str]] = None,
        confidence: float = 0.0,
    ) -> None:
        trace = ReasoningTrace(
            step=step,
            thinking=thinking,
            evidence=evidence or [],
            confidence=confidence,
        )
        self._reasoning_trace.append(trace)

        if len(self._reasoning_trace) > self.max_entries:
            self._reasoning_trace = self._reasoning_trace[-self.max_entries :]

    def get_reasoning_trace(self) -> List[ReasoningTrace]:
        return self._reasoning_trace.copy()

    def clear(self) -> None:
        self._entries.clear()
        self._reasoning_trace.clear()

    def _evict_oldest(self) -> None:
        if not self._entries:
            return
        oldest_key = min(
            self._entries.keys(), key=lambda k: self._entries[k].updated_at
        )
        self._entries.pop(oldest_key, None)

    def _is_expired(self, entry: MemoryEntry) -> bool:
        if entry.expires_at is None:
            return False
        return time.time() > entry.expires_at

    def _cleanupExpired(self) -> None:
        expired = [
            eid for eid, entry in self._entries.items() if self._is_expired(entry)
        ]
        for eid in expired:
            self._entries.pop(eid, None)


class ProjectMemory:
    def __init__(self, max_entries: int = 1000):
        self.max_entries = max_entries
        self._entries: Dict[str, MemoryEntry] = {}
        self._project_index: Dict[str, set] = {}

    def store(
        self,
        project: str,
        key: str,
        value: Any,
        metadata: Optional[Dict] = None,
    ) -> str:
        if len(self._entries) >= self.max_entries:
            self._evict_lru(project)

        entry_id = f"pm_{project}_{key}_{int(time.time() * 1000)}"

        self._entries[entry_id] = MemoryEntry(
            entry_id=entry_id,
            tier=MemoryTier.PROJECT.value,
            scope=f"project:{project}",
            key=key,
            value=value,
            metadata=metadata or {},
        )

        if project not in self._project_index:
            self._project_index[project] = set()
        self._project_index[project].add(entry_id)

        return entry_id

    def retrieve(self, project: str, key: str) -> Optional[Any]:
        for entry_id in self._project_index.get(project, set()):
            entry = self._entries.get(entry_id)
            if entry and entry.key == key:
                entry.access_count += 1
                entry.updated_at = time.time()
                return entry.value
        return None

    def retrieve_all_project(self, project: str) -> List[MemoryEntry]:
        entries = []
        for entry_id in self._project_index.get(project, set()):
            entry = self._entries.get(entry_id)
            if entry:
                entries.append(entry)
        return sorted(entries, key=lambda e: e.updated_at, reverse=True)

    def search_project(self, project: str, query: str) -> List[MemoryEntry]:
        results = []
        query_lower = query.lower()

        for entry in self.retrieve_all_project(project):
            if query_lower in entry.key.lower():
                results.append(entry)
            elif isinstance(entry.value, str) and query_lower in entry.value.lower():
                results.append(entry)
        return results

    def delete_project(self, project: str) -> int:
        entry_ids = self._project_index.pop(project, set())
        for entry_id in entry_ids:
            self._entries.pop(entry_id, None)
        return len(entry_ids)

    def _evict_lru(self, project: str) -> None:
        entries = self.retrieve_all_project(project)
        if entries:
            oldest = entries[-1]
            self._entries.pop(oldest.entry_id, None)
            self._project_index[project].discard(oldest.entry_id)


class LongTermMemory:
    def __init__(
        self,
        backend_url: Optional[str] = None,
        max_entries: int = 10000,
    ):
        self.backend_url = backend_url or "http://localhost:6333"
        self.max_entries = max_entries
        self._entries: Dict[str, MemoryEntry] = {}
        self._last_sync: float = 0

    async def store(
        self,
        scope: str,
        key: str,
        value: Any,
        metadata: Optional[Dict] = None,
    ) -> str:
        entry_id = f"ltm_{scope}_{key}_{int(time.time() * 1000)}"

        self._entries[entry_id] = MemoryEntry(
            entry_id=entry_id,
            tier=MemoryTier.LONG_TERM.value,
            scope=scope,
            key=key,
            value=value,
            metadata=metadata or {},
        )

        await self._persist_entry(entry_id)

        return entry_id

    async def retrieve(self, scope: str, key: str) -> Optional[Any]:
        for entry in self._entries.values():
            if entry.scope == scope and entry.key == key:
                return entry.value
        return await self._fetch_from_backend(scope, key)

    async def search(
        self,
        scope: str,
        query: str,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        results = []
        query_lower = query.lower()

        for entry in self._entries.values():
            if entry.scope != scope:
                continue
            if query_lower in entry.key.lower():
                results.append(entry)
            elif isinstance(entry.value, str) and query_lower in entry.value.lower():
                results.append(entry)

        return results[:limit]

    async def sync(self) -> Dict[str, int]:
        synced = {"uploaded": 0, "downloaded": 0}

        for entry in self._entries.values():
            if entry.updated_at > self._last_sync:
                await self._persist_entry(entry.entry_id)
                synced["uploaded"] += 1

        synced["downloaded"] = await self._load_recent(scope="global")
        self._last_sync = time.time()

        return synced

    async def _persist_entry(self, entry_id: str) -> None:
        entry = self._entries.get(entry_id)
        if not entry:
            return

        try:
            async with httpx.AsyncClient() as client:
                await client.put(
                    f"{self.backend_url}/collections/memory/points",
                    json={
                        "points": [
                            {
                                "id": entry_id,
                                "vector": [],
                                "payload": {
                                    "tier": entry.tier,
                                    "scope": entry.scope,
                                    "key": entry.key,
                                    "value": json.dumps(entry.value),
                                    "metadata": entry.metadata,
                                    "created_at": entry.created_at,
                                },
                            }
                        ]
                    },
                    timeout=10.0,
                )
        except Exception as e:
            logger.warning("Error saving to memory backend: %s", e)

    async def _fetch_from_backend(self, scope: str, key: str) -> Optional[Any]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.backend_url}/collections/memory/points/search",
                    json={
                        "filter": {
                            "must": [
                                {"key": "scope", "match": scope},
                                {"key": "key", "match": key},
                            ]
                        },
                        "limit": 1,
                    },
                    timeout=10.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("result", [])
                    if results:
                        return json.loads(
                            results[0].get("payload", {}).get("value", "{}")
                        )
        except Exception as e:
            logger.warning("Error fetching from memory backend: %s", e)
        return None

    async def _load_recent(self, scope: str) -> int:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.backend_url}/collections/memory/points/search",
                    json={
                        "filter": {"must": [{"key": "scope", "match": scope}]},
                        "limit": 100,
                    },
                    timeout=10.0,
                )
                if response.status_code == 200:
                    return len(response.json().get("result", []))
        except Exception as e:
            logger.warning("Error loading recent from memory backend: %s", e)
        return 0


class MemorySystem:
    def __init__(
        self,
        session_id: Optional[str] = None,
        project: Optional[str] = None,
    ):
        self.session_id = session_id or "default"
        self.project = project or "default"

        self.short_term = ShortTermMemory()
        self.project_memory = ProjectMemory()
        self.long_term = LongTermMemory()

    async def remember(
        self,
        key: str,
        value: Any,
        tier: MemoryTier = MemoryTier.SHORT_TERM,
        metadata: Optional[Dict] = None,
    ) -> str:
        if tier == MemoryTier.SHORT_TERM:
            return self.short_term.store(key, value, metadata)
        elif tier == MemoryTier.PROJECT:
            return self.project_memory.store(self.project, key, value, metadata)
        elif tier == MemoryTier.LONG_TERM:
            import asyncio

            loop = asyncio.get_running_loop()
            return await loop.create_task(
                self.long_term.store(f"project:{self.project}", key, value, metadata)
            )
        return ""

    async def recall(
        self,
        key: str,
        tier: Optional[MemoryTier] = None,
    ) -> Optional[Any]:
        if tier is None or tier == MemoryTier.SHORT_TERM:
            result = self.short_term.retrieve(key)
            if result is not None:
                return result

        if tier is None or tier == MemoryTier.PROJECT:
            result = self.project_memory.retrieve(self.project, key)
            if result is not None:
                return result

        if tier is None or tier == MemoryTier.LONG_TERM:
            import asyncio

            loop = asyncio.get_running_loop()
            result = await loop.create_task(
                self.long_term.retrieve(f"project:{self.project}", key)
            )
            if result is not None:
                return result

        return None

    def get_context(self, max_entries: int = 10) -> Dict[str, Any]:
        recent_stm = self.short_term.retrieve_recent(max_entries)
        recent_project = self.project_memory.retrieve_all_project(self.project)
        reasoning = self.short_term.get_reasoning_trace()

        return {
            "session_id": self.session_id,
            "project": self.project,
            "recent_short_term": [
                {"key": e.key, "value": e.value, "updated_at": e.updated_at}
                for e in recent_stm
            ],
            "recent_project": [
                {"key": e.key, "value": e.value, "updated_at": e.updated_at}
                for e in recent_project[:max_entries]
            ],
            "reasoning_trace": [
                {
                    "step": r.step,
                    "thinking": r.thinking,
                    "evidence": r.evidence,
                    "confidence": r.confidence,
                }
                for r in reasoning
            ],
        }

    def add_trace(
        self,
        step: str,
        thinking: str,
        evidence: Optional[List[str]] = None,
        confidence: float = 0.0,
    ) -> None:
        self.short_term.add_reasoning_trace(step, thinking, evidence, confidence)


_short_term_memory: Optional[ShortTermMemory] = None
_memory_systems: Dict[str, "MemorySystem"] = {}


def get_short_term_memory() -> ShortTermMemory:
    global _short_term_memory
    if _short_term_memory is None:
        _short_term_memory = ShortTermMemory()
    return _short_term_memory


def get_memory_system(
    session_id: Optional[str] = None,
    project: Optional[str] = None,
) -> MemorySystem:
    key = f"{session_id or 'default'}_{project or 'default'}"

    global _memory_systems
    if key not in _memory_systems:
        _memory_systems[key] = MemorySystem(session_id, project)
    return _memory_systems[key]
