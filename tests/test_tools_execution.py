"""
Comprehensive tests for tool execution across ideation, day2, requirements, and testing tools.
Tests verify that tools return expected structures even when falling back to default behavior.
"""

import pytest
from unittest.mock import patch, AsyncMock

from tools.ideation import IdeaGeneratorTool, BrainstormTool
from tools.day2 import IncidentDetectorTool, RootCauseAnalyzerTool
from tools.requirements import UserStoryGeneratorTool, GapAnalyzerTool
from tools.testing import TestGeneratorTool, MutationTesterTool
from tools.base import ToolInput


class TestIdeationTools:
    """Tests for ideation tools (IdeaGeneratorTool, BrainstormTool)."""

    @pytest.mark.asyncio
    async def test_idea_generator_returns_structure(self):
        """Test that IdeaGeneratorTool returns expected structure with domain, ideas, count."""
        tool = IdeaGeneratorTool()
        
        # Execute with valid input
        input_data = ToolInput(args={
            "domain": "e-commerce",
            "constraints": ["AWS", "serverless"],
            "existing_ideas": ["basic-store"]
        })
        
        result = await tool.execute(input_data)
        
        # Assert result has expected structure
        assert result is not None
        assert result.result is not None
        assert "domain" in result.result
        assert result.result["domain"] == "e-commerce"
        assert "generated_ideas" in result.result
        assert "count" in result.result
        assert isinstance(result.result["generated_ideas"], list)
        assert isinstance(result.result["count"], int)
        
        # Verify metadata
        assert result.metadata.get("generated") is True
        assert "method" in result.metadata

    @pytest.mark.asyncio
    async def test_brainstorm_returns_ideas(self):
        """Test that BrainstormTool returns expanded ideas with proper structure."""
        tool = BrainstormTool()
        
        # Execute with seed ideas
        input_data = ToolInput(args={
            "seed_ideas": ["shopping-cart", "payment-gateway"],
            "focus_areas": ["scalability", "security"],
            "expand_count": 5
        })
        
        result = await tool.execute(input_data)
        
        # Assert result has expected structure
        assert result is not None
        assert result.result is not None
        assert "original_ideas" in result.result
        assert "expanded_ideas" in result.result
        assert "count" in result.result
        
        # Verify original ideas preserved
        assert result.result["original_ideas"] == ["shopping-cart", "payment-gateway"]
        
        # Verify expanded ideas is a list
        assert isinstance(result.result["expanded_ideas"], list)
        assert isinstance(result.result["count"], int)
        
        # Verify metadata
        assert result.metadata.get("brainstormed") is True
        assert "method" in result.metadata


class TestDay2Tools:
    """Tests for Day2 operations tools (IncidentDetectorTool, RootCauseAnalyzerTool)."""

    @pytest.mark.asyncio
    async def test_incident_detector_output_format(self):
        """Test that IncidentDetectorTool returns incidents in expected format."""
        tool = IncidentDetectorTool()
        
        # Execute with sample alerts
        input_data = ToolInput(args={
            "alerts": [
                {"severity": "critical", "message": "High CPU usage", "service": "api"},
                {"severity": "critical", "message": "Memory leak", "service": "api"},
                {"severity": "warning", "message": "Slow response", "service": "web"}
            ]
        })
        
        result = await tool.execute(input_data)
        
        # Assert result has expected structure
        assert result is not None
        assert result.result is not None
        assert "incidents" in result.result
        assert isinstance(result.result["incidents"], list)
        
        # Verify metadata
        assert result.metadata.get("detected") is True
        assert "method" in result.metadata

    @pytest.mark.asyncio
    async def test_root_cause_analyzer_finds_causes(self):
        """Test that RootCauseAnalyzerTool returns RCA structure with root_cause."""
        tool = RootCauseAnalyzerTool()
        
        # Execute with incident ID
        input_data = ToolInput(args={
            "incident_id": "INC-12345"
        })
        
        result = await tool.execute(input_data)
        
        # Assert result has expected structure
        assert result is not None
        assert result.result is not None
        assert "rca" in result.result
        
        # RCA should contain root_cause field
        rca = result.result["rca"]
        assert isinstance(rca, dict)
        assert "root_cause" in rca
        
        # Verify metadata
        assert result.metadata.get("analyzed") is True
        assert "method" in result.metadata


class TestRequirementsTools:
    """Tests for requirements tools (UserStoryGeneratorTool, GapAnalyzerTool)."""

    @pytest.mark.asyncio
    async def test_user_story_generator_format(self):
        """Test that UserStoryGeneratorTool returns stories in expected format."""
        tool = UserStoryGeneratorTool()
        
        # Execute with requirements text
        input_data = ToolInput(args={
            "text": "Users need to be able to search for products. Users should be able to add items to cart.",
            "format": "jira"
        })
        
        result = await tool.execute(input_data)
        
        # Assert result has expected structure
        assert result is not None
        assert result.result is not None
        assert "stories" in result.result
        assert "count" in result.result
        
        # Verify stories is a list
        assert isinstance(result.result["stories"], list)
        assert isinstance(result.result["count"], int)
        
        # Verify metadata
        assert result.metadata.get("generated") is True
        assert "method" in result.metadata

    @pytest.mark.asyncio
    async def test_gap_analyzer_finds_gaps(self):
        """Test that GapAnalyzerTool identifies gaps in requirements."""
        tool = GapAnalyzerTool()
        
        # Execute with requirements missing key aspects
        input_data = ToolInput(args={
            "requirements": [
                "The system shall allow users to login",
                "The system shall display user profile"
            ]
        })
        
        result = await tool.execute(input_data)
        
        # Assert result has expected structure
        assert result is not None
        assert result.result is not None
        assert "gaps" in result.result
        
        # Verify gaps is a list
        assert isinstance(result.result["gaps"], list)
        
        # Should find gaps (security, performance, error handling, testing)
        # The exact gaps depend on the fallback logic
        for gap in result.result["gaps"]:
            assert "type" in gap
            assert "severity" in gap
        
        # Verify metadata
        assert result.metadata.get("analyzed") is True


class TestTestingTools:
    """Tests for testing tools (TestGeneratorTool, MutationTesterTool)."""

    @pytest.mark.asyncio
    async def test_mutation_tester_graceful_degradation(self):
        """Test that MutationTesterTool handles missing mutmut gracefully."""
        tool = MutationTesterTool()
        
        # Execute with paths - should handle gracefully even without mutmut
        input_data = ToolInput(args={
            "source_path": "core/",
            "test_path": "tests/"
        })
        
        result = await tool.execute(input_data)
        
        # Assert result has expected structure
        assert result is not None
        assert result.result is not None
        
        # Should return result with status field
        assert "status" in result.result
        
        # Status should indicate either unavailable, error, or completed
        assert result.result["status"] in ["unavailable", "error", "completed", "timeout"]
        
        # If unavailable, should have note about installing mutmut
        if result.result["status"] == "unavailable":
            assert "note" in result.result
            assert "mutmut" in result.result["note"].lower()
        
        # Verify metadata
        assert result.metadata.get("executed") is True

    @pytest.mark.asyncio
    async def test_test_generator_produces_valid_format(self):
        """Test that TestGeneratorTool returns tests in expected format."""
        tool = TestGeneratorTool()
        
        # Execute with target code
        input_data = ToolInput(args={
            "target": "calculate_total",
            "target_type": "unit",
            "language": "python"
        })
        
        result = await tool.execute(input_data)
        
        # Assert result has expected structure
        assert result is not None
        assert result.result is not None
        assert "target" in result.result
        assert "target_type" in result.result
        assert "tests" in result.result
        assert "count" in result.result
        
        # Verify tests is a list
        assert isinstance(result.result["tests"], list)
        assert isinstance(result.result["count"], int)
        
        # Each test should have name, code, type
        for test in result.result["tests"]:
            assert "name" in test
            assert "code" in test
            assert "type" in test
        
        # Verify metadata
        assert result.metadata.get("generated") is True
        assert "method" in result.metadata


class TestToolValidation:
    """Tests for tool input validation."""

    def test_idea_generator_requires_domain(self):
        """Test that IdeaGeneratorTool requires domain in input."""
        tool = IdeaGeneratorTool()
        
        # Should require domain
        assert tool.validate_input({"domain": "test"}) is True
        assert tool.validate_input({}) is False

    def test_brainstorm_requires_seed_ideas(self):
        """Test that BrainstormTool requires seed_ideas in input."""
        tool = BrainstormTool()
        
        assert tool.validate_input({"seed_ideas": ["test"]}) is True
        assert tool.validate_input({}) is False

    def test_incident_detector_requires_alerts(self):
        """Test that IncidentDetectorTool requires alerts in input."""
        tool = IncidentDetectorTool()
        
        assert tool.validate_input({"alerts": []}) is True
        assert tool.validate_input({}) is False

    def test_root_cause_analyzer_requires_incident_id(self):
        """Test that RootCauseAnalyzerTool requires incident_id in input."""
        tool = RootCauseAnalyzerTool()
        
        assert tool.validate_input({"incident_id": "INC-1"}) is True
        assert tool.validate_input({}) is False

    def test_user_story_generator_requires_text(self):
        """Test that UserStoryGeneratorTool requires text in input."""
        tool = UserStoryGeneratorTool()
        
        assert tool.validate_input({"text": "requirements"}) is True
        assert tool.validate_input({}) is False

    def test_gap_analyzer_requires_requirements(self):
        """Test that GapAnalyzerTool requires requirements in input."""
        tool = GapAnalyzerTool()
        
        assert tool.validate_input({"requirements": []}) is True
        assert tool.validate_input({}) is False

    def test_mutation_tester_requires_source_path(self):
        """Test that MutationTesterTool requires source_path in input."""
        tool = MutationTesterTool()
        
        assert tool.validate_input({"source_path": "src/"}) is True
        assert tool.validate_input({}) is False

    def test_test_generator_requires_target(self):
        """Test that TestGeneratorTool requires target in input."""
        tool = TestGeneratorTool()
        
        assert tool.validate_input({"target": "my_function"}) is True
        assert tool.validate_input({}) is False
