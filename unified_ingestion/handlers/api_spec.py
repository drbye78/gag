import hashlib
import json
import logging
from typing import Any, Dict

from documents.diagram_formats import OpenAPIParser
from unified_ingestion.handlers.base import Handler, HandlerResult

logger = logging.getLogger(__name__)


class APISpecHandler(Handler):
    async def handle(
        self, content: bytes, source_id: str, metadata: Dict[str, Any]
    ) -> HandlerResult:
        filename = metadata.get("filename", "api spec")
        text = content.decode("utf-8")

        try:
            if filename.endswith(".json"):
                spec = json.loads(text)
            elif filename.endswith((".yaml", ".yml")):
                import yaml

                spec = yaml.safe_load(text)
            else:
                spec = self._try_parse(text)

            if not spec:
                return HandlerResult(success=False, error="Could not parse OpenAPI spec")

            parser = OpenAPIParser()
            result = parser.parse(spec)

            chunks = []
            for path, methods in result.paths.items():
                for method, op in methods.items():
                    chunk_id = hashlib.sha256(f"{source_id}:{path}:{method}".encode()).hexdigest()[
                        :16
                    ]
                    chunks.append(
                        {
                            "id": chunk_id,
                            "content": json.dumps(op),
                            "chunk_index": len(chunks),
                            "start_char": 0,
                            "end_char": 0,
                            "metadata": {
                                "source_id": source_id,
                                "filename": filename,
                                "path": path,
                                "method": method,
                            },
                        }
                    )

            entities = []
            for schema in result.schemas:
                entities.append(
                    {
                        "name": schema.get("name"),
                        "type": "schema",
                        "properties": schema.get("properties"),
                    }
                )

            for security_scheme in result.security_schemes:
                entities.append(
                    {
                        "name": security_scheme.get("name"),
                        "type": security_scheme.get("type"),
                        "scheme": security_scheme.get("scheme"),
                    }
                )

            relationships = []
            for path, methods in result.paths.items():
                for method, op in methods.items():
                    if "tags" in op:
                        for tag in op.get("tags", []):
                            relationships.append(
                                {
                                    "source": f"{path}:{method}",
                                    "target": tag,
                                    "type": "tagged",
                                }
                            )

            return HandlerResult(
                success=True,
                chunks=chunks,
                entities=entities,
                relationships=relationships,
                metadata={
                    "version": result.version,
                    "path_count": len(result.paths),
                    "schema_count": len(result.schemas),
                },
            )

        except Exception as e:
            logger.error("APISpecHandler failed: %s", e)
            return HandlerResult(success=False, error=str(e))

    def _try_parse(self, text: str) -> Dict[str, Any]:
        try:
            import yaml

            return yaml.safe_load(text)
        except Exception:
            pass

        try:
            return json.loads(text)
        except Exception:
            pass

        return {}
