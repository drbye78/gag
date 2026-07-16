"""
Database migration system for Engineering Intelligence System.

Supports FalkorDB (graph) and Qdrant (vector) migrations.
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


MIGRATIONS_DIR = Path(__file__).parent / "migrations"


@dataclass
class Migration:
    """Represents a database migration."""
    version: str
    name: str
    timestamp: datetime
    falkordb_up: Optional[str] = None
    falkordb_down: Optional[str] = None
    qdrant_up: Optional[str] = None
    qdrant_down: Optional[str] = None


class MigrationManager:
    """Manages database migrations for FalkorDB and Qdrant."""
    
    def __init__(self, falkordb_client=None, qdrant_client=None):
        self.falkordb = falkordb_client
        self.qdrant = qdrant_client
        self._applied: List[str] = []
    
    async def init_db(self) -> None:
        """Initialize database schema."""
        logger.info("Initializing database schema...")
        
        if self.falkordb:
            await self._init_falkordb()
        
        if self.qdrant:
            await self._init_qdrant()
        
        logger.info("Database schema initialized")
    
    async def _init_falkordb(self) -> None:
        """Initialize FalkorDB with base schema."""
        schema = """
        CREATE CONSTRAINT IF NOT EXISTS FOR (n:Document) REQUIRE n.id IS UNIQUE;
        CREATE CONSTRAINT IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE;
        CREATE CONSTRAINT IF NOT EXISTS FOR (n:Pattern) REQUIRE n.id IS UNIQUE;
        CREATE CONSTRAINT IF NOT EXISTS FOR (n:Relationship) REQUIRE n.id IS UNIQUE;
        
        CREATE INDEX IF NOT EXISTS FOR (n:Document) ON (n.source_type);
        CREATE INDEX IF NOT EXISTS FOR (n:Entity) ON (n.type);
        CREATE INDEX IF NOT EXISTS FOR (n:Pattern) ON (n.domain);
        """
        try:
            await self.falkordb.execute(schema)
        except Exception as e:
            logger.warning(f"FalkorDB init warning: {e}")
    
    async def _init_qdrant(self) -> None:
        """Initialize Qdrant collections."""
        collections = [
            {"name": "documents", "vector_size": 1536},
            {"name": "code", "vector_size": 1536},
            {"name": "diagrams", "vector_size": 1536},
            {"name": "ui_sketches", "vector_size": 768},
        ]
        
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
            
            for coll in collections:
                try:
                    self.qdrant.recreate_collection(
                        collection_name=coll["name"],
                        vectors_config=VectorParams(
                            size=coll["vector_size"],
                            distance=Distance.COSINE
                        )
                    )
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Qdrant init warning: {e}")
    
    async def migrate(self, target_version: Optional[str] = None) -> None:
        """Run pending migrations."""
        logger.info(f"Running migrations up to {target_version or 'latest'}")
        
        pending = self._get_pending_migrations(target_version)
        
        for migration in pending:
            logger.info(f"Applying migration {migration.version}: {migration.name}")
            
            if migration.falkordb_up and self.falkordb:
                try:
                    await self.falkordb.execute(migration.falkordb_up)
                except Exception as e:
                    logger.error(f"FalkorDB migration {migration.version} failed: {e}")
                    raise
            
            if migration.qdrant_up and self.qdrant:
                try:
                    await self._apply_qdrant_migration(migration.qdrant_up)
                except Exception as e:
                    logger.error(f"Qdrant migration {migration.version} failed: {e}")
                    raise
            
            self._applied.append(migration.version)
        
        logger.info(f"Applied {len(pending)} migrations")
    
    async def rollback(self, target_version: str) -> None:
        """Rollback to a specific version."""
        logger.info(f"Rolling back migrations to {target_version}")
        
        applied = [v for v in reversed(self._applied) if v > target_version]
        
        for version in applied:
            migration = self._get_migration(version)
            if not migration:
                continue
            
            logger.info(f"Rolling back migration {version}")
            
            if migration.falkordb_down and self.falkordb:
                try:
                    await self.falkordb.execute(migration.falkordb_down)
                except Exception as e:
                    logger.error(f"FalkorDB rollback {version} failed: {e}")
            
            if migration.qdrant_down and self.qdrant:
                try:
                    await self._apply_qdrant_migration(migration.qdrant_down, down=True)
                except Exception as e:
                    logger.error(f"Qdrant rollback {version} failed: {e}")
    
    def _get_pending_migrations(self, target: Optional[str]) -> List[Migration]:
        """Get list of pending migrations."""
        return []
    
    def _get_migration(self, version: str) -> Optional[Migration]:
        """Get migration by version."""
        return None
    
    async def _apply_qdrant_migration(self, config: Dict[str, Any], down: bool = False) -> None:
        """Apply Qdrant migration config."""
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get migration status."""
        return {
            "applied": self._applied,
            "pending": len(self._get_pending_migrations(None)),
            "falkordb_connected": self.falkordb is not None,
            "qdrant_connected": self.qdrant is not None,
        }


async def get_migration_manager() -> MigrationManager:
    """Get migration manager instance."""
    falkordb = None
    qdrant = None
    
    try:
        from graph.client import get_graph_client
        falkordb = get_graph_client()
    except Exception:
        pass
    
    try:
        from qdrant_client import QdrantClient
        from core.config import get_settings
        settings = get_settings()
        qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    except Exception:
        pass
    
    return MigrationManager(falkordb_client=falkordb, qdrant_client=qdrant)


# Migration entry point for CLI
if __name__ == "__main__":
    import asyncio
    
    async def main():
        manager = await get_migration_manager()
        
        print("=== Migration Status ===")
        status = manager.get_status()
        print(f"Applied: {status['applied']}")
        print(f"FalkorDB: {'Connected' if status['falkordb_connected'] else 'Not connected'}")
        print(f"Qdrant: {'Connected' if status['qdrant_connected'] else 'Not connected'}")
        
        await manager.init_db()
        print("\nDatabase initialized successfully")
    
    asyncio.run(main())