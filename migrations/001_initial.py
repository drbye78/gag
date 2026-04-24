"""
Initial migration - Create base schema.

Version: 001
Timestamp: 2026-04-24
"""

INIT_FALKORDB = """
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Document) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Pattern) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Relationship) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:UseCase) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:ADR) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:ReferenceArch) REQUIRE n.id IS UNIQUE;

CREATE INDEX IF NOT EXISTS FOR (n:Document) ON (n.source_type);
CREATE INDEX IF NOT EXISTS FOR (n:Document) ON (n.created_at);
CREATE INDEX IF NOT EXISTS FOR (n:Entity) ON (n.type);
CREATE INDEX IF NOT EXISTS FOR (n:Entity) ON (n.name);
CREATE INDEX IF NOT EXISTS FOR (n:Pattern) ON (n.domain);
CREATE INDEX IF NOT EXISTS FOR (n:Pattern) ON (n.priority);
CREATE INDEX IF NOT EXISTS FOR (n:Relationship) ON (n.type);
CREATE INDEX IF NOT EXISTS FOR (n:UseCase) ON (n.platform);
CREATE INDEX IF NOT EXISTS FOR (n:ADR) ON (n.status);
"""

DROP_FALKORDB = """
DROP CONSTRAINT FOR (n:Document) REQUIRE n.id IS UNIQUE;
DROP CONSTRAINT FOR (n:Entity) REQUIRE n.id IS UNIQUE;
DROP CONSTRAINT FOR (n:Pattern) REQUIRE n.id IS UNIQUE;
DROP CONSTRAINT FOR (n:Relationship) REQUIRE n.id IS UNIQUE;
DROP CONSTRAINT FOR (n:UseCase) REQUIRE n.id IS UNIQUE;
DROP CONSTRAINT FOR (n:ADR) REQUIRE n.id IS UNIQUE;
DROP CONSTRAINT FOR (n:ReferenceArch) REQUIRE n.id IS UNIQUE;
"""

INIT_QDRANT = {
    "collections": [
        {
            "name": "documents",
            "vector_size": 1536,
            "distance": "Cosine",
            "payload_schema": {
                "source_type": "keyword",
                "source_id": "keyword",
                "content_hash": "keyword",
                "created_at": "datetime",
                "metadata": "json"
            }
        },
        {
            "name": "code",
            "vector_size": 1536,
            "distance": "Cosine",
            "payload_schema": {
                "file_path": "keyword",
                "language": "keyword",
                "function_name": "keyword",
                "class_name": "keyword"
            }
        },
        {
            "name": "diagrams",
            "vector_size": 1536,
            "distance": "Cosine",
            "payload_schema": {
                "diagram_type": "keyword",
                "format": "keyword",
                "entities": "json",
                "relationships": "json"
            }
        },
        {
            "name": "ui_sketches",
            "vector_size": 768,
            "distance": "Cosine",
            "payload_schema": {
                "sketch_type": "keyword",
                "components": "json",
                "layout": "json"
            }
        }
    ]
}

DROP_QDRANT = {
    "collections": ["documents", "code", "diagrams", "ui_sketches"]
}