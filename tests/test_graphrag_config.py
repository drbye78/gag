import pytest
from core.config import Settings, reset_settings


def test_graphrag_config_defaults():
    reset_settings()
    settings = Settings()

    assert settings.graphrag_enabled == False
    assert settings.graphrag_use_llm_extraction == False
    assert settings.graphrag_structural_chunking == True
    assert settings.graphrag_incremental == True
    assert settings.graphrag_community_detection == True
    assert settings.graphrag_max_entities == 100
    assert settings.graphrag_default_hops == 3


def test_graphrag_entity_types_default():
    reset_settings()
    settings = Settings()

    assert "PERSON" in settings.graphrag_entity_types
    assert "ORGANIZATION" in settings.graphrag_entity_types
    assert "CONCEPT" in settings.graphrag_entity_types
    assert "TECHNOLOGY" in settings.graphrag_entity_types


def test_graphrag_relationship_types_default():
    reset_settings()
    settings = Settings()

    assert "RELATED_TO" in settings.graphrag_relationship_types
    assert "DEPENDS_ON" in settings.graphrag_relationship_types
    assert "REFERENCES" in settings.graphrag_relationship_types


def test_graphrag_config_env_override(monkeypatch):
    monkeypatch.setenv("GRAPH_RAG_ENABLED", "true")
    monkeypatch.setenv("GRAPH_RAG_USE_LLM", "true")
    monkeypatch.setenv("GRAPH_RAG_MAX_ENTITIES", "500")
    monkeypatch.setenv("GRAPH_RAG_DEFAULT_HOPS", "5")
    monkeypatch.setenv("GRAPH_RAG_ENTITY_TYPES", "PERSON,TECHNOLOGY,DOCUMENT")
    reset_settings()
    settings = Settings()

    assert settings.graphrag_enabled == True
    assert settings.graphrag_use_llm_extraction == True
    assert settings.graphrag_max_entities == 500
    assert settings.graphrag_default_hops == 5
    assert settings.graphrag_entity_types == ["PERSON", "TECHNOLOGY", "DOCUMENT"]


def test_graphrag_config_disabled_by_default():
    reset_settings()
    settings = Settings()

    assert settings.graphrag_enabled == False