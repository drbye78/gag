"""Tools module — lazy import to avoid cascading dependency loading."""

__all__ = ["CodeAnalysisTools", "get_code_analysis_tools"]

def __getattr__(name):
    if name in ("CodeAnalysisTools", "get_code_analysis_tools"):
        from tools.code_analysis import CodeAnalysisTools, get_code_analysis_tools
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
