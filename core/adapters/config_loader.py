"""Platform adapter YAML config loader with hot-reload support.

Loads platform-specific patterns, services, and constraints from YAML files.
Supports hot reload via file watcher and Redis pub/sub notifications.
"""
import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

logger = logging.getLogger(__name__)

# Root directory for adapter configs — relative to project root
DEFAULT_CONFIG_ROOT = Path("config/adapters")


class AdapterConfigLoader:
    """Loads and caches YAML configs per platform with hot-reload support."""
    
    def __init__(self, config_root: Optional[Path] = None):
        self.config_root = config_root or DEFAULT_CONFIG_ROOT
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._watchers: Dict[str, asyncio.Task] = {}
        self._redis = None
        self._redis_url: Optional[str] = None
    
    def set_redis(self, redis_url: str):
        """Enable Redis pub/sub for cross-process hot reload."""
        self._redis_url = redis_url
    
    async def _get_redis(self):
        if self._redis is None and self._redis_url:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(self._redis_url)
            # Subscribe to config change notifications
            asyncio.create_task(self._subscribe_config_changes())
        return self._redis
    
    async def _subscribe_config_changes(self):
        redis = await self._get_redis()
        if not redis:
            return
        pubsub = redis.pubsub()
        await pubsub.subscribe("adapter:config:reload")
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    platform = message["data"].decode("utf-8")
                    self.invalidate_cache(platform)
                    logger.info("Hot-reloaded config for platform: %s", platform)
        except asyncio.CancelledError:
            await pubsub.unsubscribe("adapter:config:reload")
    
    def invalidate_cache(self, platform: str) -> None:
        """Clear cached configs for a platform (called on reload)."""
        keys_to_remove = [k for k in self._cache if k.startswith(f"{platform}:")]
        for key in keys_to_remove:
            del self._cache[key]
    
    def load_patterns(self, platform: str) -> List[Dict[str, Any]]:
        """Load platform patterns from YAML."""
        cache_key = f"{platform}:patterns"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        path = self.config_root / platform / "patterns.yaml"
        if not path.exists():
            logger.debug("No patterns config for %s at %s", platform, path)
            return []
        
        with open(path) as f:
            data = yaml.safe_load(f)
        
        patterns = data.get("patterns", []) if data else []
        self._cache[cache_key] = patterns
        return patterns
    
    def load_services(self, platform: str) -> Dict[str, List[str]]:
        """Load platform service catalog from YAML.
        
        Returns:
            Dict with keys like "compute", "storage", "networking", etc.
            Each value is a list of service IDs.
        """
        cache_key = f"{platform}:services"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        path = self.config_root / platform / "services.yaml"
        if not path.exists():
            logger.debug("No services config for %s at %s", platform, path)
            return {}
        
        with open(path) as f:
            data = yaml.safe_load(f)
        
        services = data.get("services", {}) if data else {}
        self._cache[cache_key] = services
        return services
    
    def load_constraints(self, platform: str) -> Dict[str, Any]:
        """Load platform constraints from YAML."""
        cache_key = f"{platform}:constraints"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        path = self.config_root / platform / "constraints.yaml"
        if not path.exists():
            logger.debug("No constraints config for %s at %s", platform, path)
            return {}
        
        with open(path) as f:
            data = yaml.safe_load(f)
        
        self._cache[cache_key] = data or {}
        return data or {}
    
    async def broadcast_reload(self, platform: str):
        """Notify all workers to reload config for a platform."""
        redis = await self._get_redis()
        if redis:
            await redis.publish("adapter:config:reload", platform)
    
    async def close(self):
        for task in self._watchers.values():
            task.cancel()
        if self._redis:
            await self._redis.close()
            self._redis = None


# Singleton
_loader: Optional[AdapterConfigLoader] = None


def get_config_loader() -> AdapterConfigLoader:
    global _loader
    if _loader is None:
        _loader = AdapterConfigLoader()
    return _loader
