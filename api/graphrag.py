import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

logger = logging.getLogger(__name__)

from models.graphrag import (
    GraphRAGQueryRequest,
    GraphRAGQueryResponse,
    EntitySearchRequest,
    EntitySearchResponse,
    RelationshipSearchRequest,
    RelationshipSearchResponse,
    CommunityResponse,
    GraphRAGStatsResponse,
)
from retrieval.hybrid import get_enhanced_hybrid_retriever
from graph.client import get_falkordb_client
from core.auth import require_authenticated


router = APIRouter(prefix="/graphrag", tags=["graphrag"], dependencies=[Depends(require_authenticated)])


@router.post("/query", response_model=GraphRAGQueryResponse)
async def graphrag_query(request: GraphRAGQueryRequest):
    retriever = get_enhanced_hybrid_retriever()

    result = await retriever.search(
        request.query,
        limit=request.max_hops,
        use_reasoning=True,
        force_graphrag=True,
    )

    entities = []
    if request.include_entities:
        entity_context = await retriever.link_query_entities(request.query, limit=10)
        entities = entity_context.get("entities", [])

    relationships = []
    communities = []
    if request.include_relationships:
        for e in entities:
            rel_result = await retriever.graph_retriever.get_connected_nodes(e.get("name", ""))
            relationships.extend(rel_result.get("connected", []))

    return GraphRAGQueryResponse(
        query=request.query,
        answer=result.get("answer", ""),
        entities=entities,
        relationships=relationships,
        communities=communities,
        confidence=result.get("confidence", 0.0),
        sources=result.get("results", []),
        took_ms=result.get("took_ms", 0),
    )


@router.get("/entities", response_model=EntitySearchResponse)
async def list_entities(
    source_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    limit: int = 100,
):
    client = get_falkordb_client()

    conditions = []
    params: Dict[str, Any] = {"limit": limit}

    if source_id:
        conditions.append("e.source_id = $source_id")
        params["source_id"] = source_id

    if entity_type:
        conditions.append("e.type = $entity_type")
        params["entity_type"] = entity_type

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    cypher = f"""
    MATCH (e:Entity)
    WHERE {where_clause}
    RETURN e
    LIMIT $limit
    """

    try:
        result = await client.execute(cypher, params)
        entities = [r.get("e", {}) for r in result.get("results", [])]
    except Exception as e:
        logger.exception("Failed to list entities: %s", e)
        entities = []

    return EntitySearchResponse(entities=entities, total=len(entities))


@router.get("/entities/{entity_id}")
async def get_entity(entity_id: str):
    client = get_falkordb_client()

    cypher = """
    MATCH (e:Entity {id: $id})
    OPTIONAL MATCH (e)-[r]->(related)
    RETURN e, collect({node: related, relationship: type(r)}) as relationships
    """

    try:
        result = await client.execute(cypher, {"id": entity_id})
        data = result.get("results", [{}])[0]
        return {
            "entity": data.get("e", {}),
            "relationships": data.get("relationships", []),
        }
    except Exception as e:
        logger.exception("Failed to get entity %s: %s", entity_id, e)
        raise HTTPException(status_code=404, detail="Entity not found")


@router.get("/relationships", response_model=RelationshipSearchResponse)
async def list_relationships(
    source_id: Optional[str] = None,
    relationship_type: Optional[str] = None,
    limit: int = 100,
):
    client = get_falkordb_client()

    conditions = []
    params: Dict[str, Any] = {"limit": limit}

    if source_id:
        conditions.append("r.source_id = $source_id")
        params["source_id"] = source_id

    if relationship_type:
        conditions.append("type(r) = $rel_type")
        params["rel_type"] = relationship_type

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    cypher = f"""
    MATCH ()-[r]->()
    WHERE {where_clause}
    RETURN r
    LIMIT $limit
    """

    try:
        result = await client.execute(cypher, params)
        relationships = [r.get("r", {}) for r in result.get("results", [])]
    except Exception as e:
        logger.exception("Failed to list relationships: %s", e)
        relationships = []

    return RelationshipSearchResponse(
        relationships=relationships, total=len(relationships)
    )


@router.get("/communities", response_model=List[CommunityResponse])
async def list_communities(
    source_id: Optional[str] = None,
    min_size: int = 1,
    limit: int = 50,
):
    client = get_falkordb_client()

    if source_id:
        cypher = """
        MATCH (c:Community)<-[:IN_COMMUNITY]-(e)
        WHERE e.source_id = $source_id
        RETURN c, collect(e) as members
        LIMIT $limit
        """
        params = {"source_id": source_id, "limit": limit}
    else:
        cypher = """
        MATCH (c:Community)<-[:IN_COMMUNITY]-(e)
        RETURN c, collect(e) as members
        LIMIT $limit
        """
        params = {"limit": limit}

    try:
        result = await client.execute(cypher, params)
        communities = []
        for r in result.get("results", []):
            c = r.get("c", {})
            members = r.get("members", [])
            communities.append(
                CommunityResponse(
                    id=c.get("id", ""),
                    name=c.get("name", ""),
                    members=[{"name": m.get("name", ""), "type": m.get("type", "")} for m in members],
                    size=len(members),
                )
            )
    except Exception as e:
        logger.exception("Failed to list communities: %s", e)
        communities = []

    return communities


@router.get("/communities/{community_id}")
async def get_community(community_id: str):
    client = get_falkordb_client()

    cypher = """
    MATCH (c:Community {id: $id})<-[:IN_COMMUNITY]-(e)
    RETURN c, collect(e) as members
    """

    try:
        result = await client.execute(cypher, {"id": community_id})
        data = result.get("results", [{}])[0]
        c = data.get("c", {})
        members = data.get("members", [])
        return CommunityResponse(
            id=c.get("id", ""),
            name=c.get("name", ""),
            members=[{"name": m.get("name", ""), "type": m.get("type", "")} for m in members],
            size=len(members),
        )
    except Exception as e:
        logger.exception("Failed to get community %s: %s", community_id, e)
        raise HTTPException(status_code=404, detail="Community not found")


@router.get("/stats", response_model=GraphRAGStatsResponse)
async def get_graphrag_stats():
    client = get_falkordb_client()

    entity_types: Dict[str, int] = {}
    relationship_types: Dict[str, int] = {}
    total_entities = 0
    total_relationships = 0
    total_communities = 0

    try:
        entity_cypher = "MATCH (e:Entity) RETURN e.type as type, count(e) as count"
        entity_result = await client.execute(entity_cypher)
        for r in entity_result.get("results", []):
            entity_types[r.get("type", "unknown")] = r.get("count", 0)
        total_entities = sum(entity_types.values())
    except Exception as e:
        logger.warning("Failed to get entity types: %s", e)

    try:
        rel_cypher = "MATCH ()-[r]->() RETURN type(r) as type, count(r) as count"
        rel_result = await client.execute(rel_cypher)
        for r in rel_result.get("results", []):
            relationship_types[r.get("type", "unknown")] = r.get("count", 0)
        total_relationships = sum(relationship_types.values())
    except Exception as e:
        logger.warning("Failed to get relationship types: %s", e)

    try:
        comm_cypher = "MATCH (c:Community) RETURN count(c) as count"
        comm_result = await client.execute(comm_cypher)
        if comm_result.get("results"):
            total_communities = comm_result["results"][0].get("count", 0)
    except Exception as e:
        logger.warning("Failed to get community count: %s", e)

    avg_entities = total_entities / max(total_communities, 1)

    return GraphRAGStatsResponse(
        total_entities=total_entities,
        total_relationships=total_relationships,
        total_communities=total_communities,
        entity_types=entity_types,
        relationship_types=relationship_types,
        avg_entities_per_community=avg_entities,
    )


app = router


__all__ = ["app"]