"""Tests for SAPDocParser."""

import pytest
from ui.sap_doc_parser import SAPDocParser


@pytest.fixture
def parser():
    return SAPDocParser()


def test_parse_component_markdown(parser):
    """Parse component markdown returns SAPComponent with correct fields."""
    markdown = """# sap.m.Table
Library: sap.m
Type: control

## Properties
- items: array of ColumnListItem
- growing: boolean

## Events
- itemPress: fired when an item is pressed
"""
    result = parser.parse_component_markdown(markdown)

    assert result is not None
    assert result.name == "sap.m.Table"
    assert result.library == "sap.m"
    assert result.component_type == "control"
    assert "items: array of ColumnListItem" in result.properties
    assert "growing: boolean" in result.properties
    assert "itemPress: fired when an item is pressed" in result.events
    assert result.complexity == 2


def test_parse_service_markdown(parser):
    """Parse service markdown returns SAPService with correct fields."""
    markdown = """# OData V4 Service
Type: odata

## Capabilities
- CRUD operations
- Batch processing
- Delta queries
"""
    result = parser.parse_service_markdown(markdown)

    assert result is not None
    assert result.name == "OData V4 Service"
    assert result.service_type == "odata"
    assert "CRUD operations" in result.capabilities
    assert "Batch processing" in result.capabilities
    assert "Delta queries" in result.capabilities


def test_parse_empty_markdown_returns_none(parser):
    """Empty or whitespace-only markdown returns None."""
    assert parser.parse_component_markdown("") is None
    assert parser.parse_component_markdown("   ") is None
    assert parser.parse_service_markdown("") is None
    assert parser.parse_service_markdown("   ") is None
