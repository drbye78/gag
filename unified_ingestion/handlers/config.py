import hashlib
import json
import logging
import os
from typing import Any, Dict

import yaml

from unified_ingestion.handlers.base import Handler, HandlerResult

logger = logging.getLogger(__name__)

toml: Any = None
TOML_AVAILABLE = False
try:
    import toml as _toml

    toml = _toml
    TOML_AVAILABLE = True
except ImportError:
    pass


class ConfigHandler(Handler):
    EXTENSION_PARSERS = {
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".env": "env",
    }

    async def handle(
        self, content: bytes, source_id: str, metadata: Dict[str, Any]
    ) -> HandlerResult:
        filename = metadata.get("filename", "config")
        ext = os.path.splitext(filename)[1].lower()

        parser_type = self.EXTENSION_PARSERS.get(ext, "json")

        try:
            if parser_type == "json":
                return await self._parse_json(content, source_id, filename)
            elif parser_type == "yaml":
                return await self._parse_yaml(content, source_id, filename)
            elif parser_type == "toml":
                return await self._parse_toml(content, source_id, filename)
            elif parser_type == "env":
                return await self._parse_env(content, source_id, filename)
            else:
                return HandlerResult(success=False, error=f"Unknown config type: {ext}")

        except Exception as e:
            logger.error("ConfigHandler failed: %s", e)
            return HandlerResult(success=False, error=str(e))

    async def _parse_json(self, content: bytes, source_id: str, filename: str) -> HandlerResult:
        try:
            data = json.loads(content.decode("utf-8"))
            return self._config_to_chunks(data, source_id, filename, "json")
        except json.JSONDecodeError as e:
            return HandlerResult(success=False, error=f"JSON parse error: {e}")

    async def _parse_yaml(self, content: bytes, source_id: str, filename: str) -> HandlerResult:
        try:
            data = yaml.safe_load(content.decode("utf-8"))
            return self._config_to_chunks(data, source_id, filename, "yaml")
        except yaml.YAMLError as e:
            return HandlerResult(success=False, error=f"YAML parse error: {e}")

    async def _parse_toml(self, content: bytes, source_id: str, filename: str) -> HandlerResult:
        if not TOML_AVAILABLE:
            text = content.decode("utf-8")
            return self._config_to_chunks({"raw": text}, source_id, filename, "toml")

        try:
            data = toml.loads(content.decode("utf-8"))
            return self._config_to_chunks(data, source_id, filename, "toml")
        except toml.TomlDecodeError as e:
            return HandlerResult(success=False, error=f"TOML parse error: {e}")

    async def _parse_env(self, content: bytes, source_id: str, filename: str) -> HandlerResult:
        lines = content.decode("utf-8").strip().split("\n")
        config = {}

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip().strip('"').strip("'")

        return self._config_to_chunks(config, source_id, filename, "env")

    def _config_to_chunks(
        self,
        data: Any,
        source_id: str,
        filename: str,
        config_type: str,
    ) -> HandlerResult:
        flat = self._flatten_dict(data)
        text = json.dumps(flat, indent=2)

        chunk_id = hashlib.sha256(f"{source_id}".encode()).hexdigest()[:16]
        chunks = [
            {
                "id": chunk_id,
                "content": text,
                "chunk_index": 0,
                "start_char": 0,
                "end_char": len(text),
                "metadata": {
                    "source_id": source_id,
                    "filename": filename,
                    "config_type": config_type,
                    "key_count": len(flat),
                },
            }
        ]

        return HandlerResult(success=True, chunks=chunks, metadata={"config_type": config_type})

    def _flatten_dict(
        self, d: Dict[str, Any], parent_key: str = "", sep: str = "."
    ) -> Dict[str, Any]:
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
