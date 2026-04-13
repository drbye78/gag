import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class KBSource(str, Enum):
    STACKOVERFLOW = "stackoverflow"
    REDDIT = "reddit"
    FORUM = "forum"


@dataclass
class KBEntry:
    entry_id: str
    source: str
    title: str
    content: str
    author: str = ""
    score: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class StackOverflowClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ):
        self.api_key = api_key or os.getenv("STACKOVERFLOW_API_KEY", "")
        self.tags = tags or []
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def search_questions(
        self,
        query: str,
        max_results: int = 25,
        tagged: Optional[List[str]] = None,
    ) -> List[KBEntry]:
        if not self.api_key:
            return []

        params = {
            "order": "desc",
            "sort": "activity",
            "intitle": query,
            "maxresults": max_results,
            "site": "stackoverflow",
            "key": self.api_key,
        }
        if tagged or self.tags:
            params["tagged"] = ";".join(tagged or self.tags)

        try:
            client = self._get_client()
            response = await client.get(
                "https://api.stackexchange.com/2.3/search/advanced",
                params=params,
            )
            response.raise_for_status()
            data = response.json()
        except Exception:
            return []

        entries = []
        for item in data.get("items", []):
            entries.append(
                KBEntry(
                    entry_id=str(item.get("question_id", "")),
                    source=KBSource.STACKOVERFLOW.value,
                    title=item.get("title", ""),
                    content=item.get("body_markdown", ""),
                    author=item.get("owner", {}).get("display_name", ""),
                    score=item.get("score", 0),
                    created_at=item.get("creation_date", 0),
                    updated_at=item.get("last_activity_date", 0),
                    tags=item.get("tags", []),
                    metadata={
                        "is_answered": item.get("is_answered", False),
                        "answer_count": item.get("answer_count", 0),
                        "view_count": item.get("view_count", 0),
                    },
                )
            )

        return entries

    async def get_answers(self, question_id: int) -> List[KBEntry]:
        if not self.api_key:
            return []

        try:
            client = self._get_client()
            response = await client.get(
                f"https://api.stackexchange.com/2.3/questions/{question_id}/answers",
                params={
                    "order": "desc",
                    "sort": "votes",
                    "site": "stackoverflow",
                    "key": self.api_key,
                },
            )
            response.raise_for_status()
            data = response.json()
        except Exception:
            return []

        entries = []
        for item in data.get("items", []):
            entries.append(
                KBEntry(
                    entry_id=str(item.get("answer_id", "")),
                    source=KBSource.STACKOVERFLOW.value,
                    title=f"Answer to question {question_id}",
                    content=item.get("body_markdown", ""),
                    author=item.get("owner", {}).get("display_name", ""),
                    score=item.get("score", 0),
                    created_at=item.get("creation_date", 0),
                    metadata={"is_accepted": item.get("is_accepted", False)},
                )
            )

        return entries


class RedditClient:
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        user_agent: str = "SAPBTP-Engine/1.0",
    ):
        self.client_id = client_id or os.getenv("REDDIT_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("REDDIT_CLIENT_SECRET", "")
        self.user_agent = user_agent
        self._client: Optional[httpx.AsyncClient] = None
        self._token: Optional[str] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={"User-Agent": self.user_agent},
                timeout=30.0,
            )
        return self._client

    async def _get_token(self) -> Optional[str]:
        if self._token:
            return self._token

        if not self.client_id or not self.client_secret:
            return None

        try:
            client = self._get_client()
            response = await client.post(
                "https://www.reddit.com/api/v1/access_token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            response.raise_for_status()
            data = response.json()
            self._token = data.get("access_token")
        except Exception as e:
            logger.error("Failed to obtain Reddit access token: %s", e)

        return self._token

    async def search_submissions(
        self,
        subreddit: str,
        query: str,
        max_results: int = 25,
    ) -> List[KBEntry]:
        token = await self._get_token()
        if not token:
            return []

        try:
            client = self._get_client()
            response = await client.get(
                f"https://oauth.reddit.com/r/{subreddit}/search",
                headers={"Authorization": f"Bearer {token}"},
                params={"q": query, "limit": max_results},
            )
            response.raise_for_status()
            data = response.json()
        except Exception:
            return []

        entries = []
        for child in data.get("data", {}).get("children", []):
            data_item = child.get("data", {})
            entries.append(
                KBEntry(
                    entry_id=data_item.get("id", ""),
                    source=KBSource.REDDIT.value,
                    title=data_item.get("title", ""),
                    content=data_item.get("selftext", ""),
                    author=data_item.get("author", ""),
                    score=data_item.get("score", 0),
                    created_at=data_item.get("created_utc", 0),
                    tags=data_item.get("link_flair_text", "").split(),
                    metadata={
                        "subreddit": data_item.get("subreddit", ""),
                        "num_comments": data_item.get("num_comments", 0),
                        "permalink": data_item.get("permalink", ""),
                    },
                )
            )

        return entries


class ForumClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.base_url = base_url or os.getenv("FORUM_BASE_URL", "")
        self.api_key = api_key or os.getenv("FORUM_API_KEY", "")
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {"User-Agent": "SAPBTP-Engine/1.0"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.AsyncClient(headers=headers, timeout=30.0)
        return self._client

    async def search_posts(
        self,
        query: str,
        max_results: int = 25,
    ) -> List[KBEntry]:
        if not self.base_url:
            return []

        try:
            client = self._get_client()
            response = await client.get(
                f"{self.base_url}/api/search",
                params={"q": query, "limit": max_results},
            )
            response.raise_for_status()
            data = response.json()
        except Exception:
            return []

        entries = []
        for post in data.get("posts", []):
            entries.append(
                KBEntry(
                    entry_id=post.get("id", ""),
                    source=KBSource.FORUM.value,
                    title=post.get("title", ""),
                    content=post.get("content", post.get("body", "")),
                    author=post.get("author", ""),
                    score=post.get("votes", post.get("score", 0)),
                    created_at=post.get("created_at", 0),
                    tags=post.get("tags", []),
                    metadata={"category": post.get("category", "")},
                )
            )

        return entries


_stackoverflow_client: Optional[StackOverflowClient] = None
_reddit_client: Optional[RedditClient] = None
_forum_client: Optional[ForumClient] = None


def get_stackoverflow_client() -> StackOverflowClient:
    global _stackoverflow_client
    if _stackoverflow_client is None:
        _stackoverflow_client = StackOverflowClient()
    return _stackoverflow_client


def get_reddit_client() -> RedditClient:
    global _reddit_client
    if _reddit_client is None:
        _reddit_client = RedditClient()
    return _reddit_client


def get_forum_client() -> ForumClient:
    global _forum_client
    if _forum_client is None:
        _forum_client = ForumClient()
    return _forum_client
