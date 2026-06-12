"""Tests for code_analysis tools."""

from unittest.mock import AsyncMock, patch

import pytest

from tools.code_analysis import CodeAnalysisTools, get_code_analysis_tools


class TestCodeAnalysisTools:
    @pytest.fixture
    def tools(self):
        return CodeAnalysisTools(repo_path="/test/repo")

    @pytest.mark.asyncio
    async def test_analyze_complexity(self, tools):
        with patch.object(tools.retriever, "get_complexity", new_callable=AsyncMock) as mock:
            mock.return_value = {"complexity": 5}
            result = await tools.analyze_complexity("test_func")
            assert result["complexity"] == 5
            mock.assert_called_once_with("test_func")

    @pytest.mark.asyncio
    async def test_find_dead_code(self, tools):
        with patch.object(tools.retriever, "get_dead_code", new_callable=AsyncMock) as mock:
            mock.return_value = {"results": [{"name": "unused_func"}]}
            result = await tools.find_dead_code()
            assert len(result["results"]) == 1

    @pytest.mark.asyncio
    async def test_find_callers(self, tools):
        with patch.object(tools.retriever, "find_callers", new_callable=AsyncMock) as mock:
            mock.return_value = {"results": [{"name": "caller1"}]}
            result = await tools.find_callers("test_func")
            assert len(result["results"]) == 1

    @pytest.mark.asyncio
    async def test_find_callees(self, tools):
        with patch.object(tools.retriever, "find_callees", new_callable=AsyncMock) as mock:
            mock.return_value = {"results": [{"name": "callee1"}]}
            result = await tools.find_callees("test_func")
            assert len(result["results"]) == 1

    @pytest.mark.asyncio
    async def test_analyze_dependencies(self, tools):
        with patch.object(tools.retriever, "get_module_deps", new_callable=AsyncMock) as mock:
            mock.return_value = {"dependencies": [{"name": "dep1"}]}
            result = await tools.analyze_dependencies("os")
            assert len(result["dependencies"]) == 1

    @pytest.mark.asyncio
    async def test_analyze_class_hierarchy(self, tools):
        with patch.object(tools.retriever, "get_class_hierarchy", new_callable=AsyncMock) as mock:
            mock.return_value = {"results": [{"name": "ParentClass"}]}
            result = await tools.analyze_class_hierarchy("ChildClass")
            assert len(result["results"]) == 1

    @pytest.mark.asyncio
    async def test_get_call_chain(self, tools):
        with patch.object(tools.retriever, "get_call_chain", new_callable=AsyncMock) as mock:
            mock.return_value = {"chain": []}
            result = await tools.get_call_chain("test_func")
            assert "chain" in result

    @pytest.mark.asyncio
    async def test_get_most_complex(self, tools):
        with patch.object(
            tools.retriever, "get_most_complex_functions", new_callable=AsyncMock
        ) as mock:
            mock.return_value = {"results": []}
            result = await tools.get_most_complex(limit=5)
            mock.assert_called_once_with(limit=5)


class TestCodeAnalysisToolsFactory:
    def test_get_code_analysis_tools(self):
        tools = get_code_analysis_tools(repo_path="/test")
        assert isinstance(tools, CodeAnalysisTools)
        assert tools.retriever.repo_path == "/test"

    def test_get_code_analysis_tools_default(self):
        tools = get_code_analysis_tools()
        assert isinstance(tools, CodeAnalysisTools)
        assert tools.retriever.repo_path is None
