import httpx

from core.config import get_settings


class OpenRouterProvider:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "openai/text-embedding-3-small",
    ):
        settings = get_settings()
        self.api_key = api_key or settings.llm_api_key or ""
        self.model = model
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(60.0, connect=10.0),
            )
        return self._client

    async def embed(self, texts: list[str]) -> list[list[float]]:
        client = await self._get_client()
        resp = await client.post(
            "https://openrouter.ai/api/v1/embeddings",
            json={"input": texts, "model": self.model},
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return [d["embedding"] for d in data.get("data", [])]

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
