"""
README claim: "5 citation styles: Parenthetical, Verbatim, Footnote, Highlight, Structured, Diagram"
Source: README.md line 86 (note: README says 5 but lists 6 -- count should be fixed to 6)
"""
import pytest


@pytest.mark.claim
@pytest.mark.parametrize("style", [
    "PARENTHETICAL", "VERBATIM", "FOOTNOTE", "HIGHLIGHT", "STRUCTURED", "DIAGRAM"
])
def test_citation_style_exists(style):
    from retrieval.citations.base import CitationStyle
    assert hasattr(CitationStyle, style), f"CitationStyle.{style} does not exist"


@pytest.mark.claim
@pytest.mark.parametrize("style", ["PARENTHETICAL", "VERBATIM", "FOOTNOTE", "HIGHLIGHT", "STRUCTURED"])
def test_citation_style_produces_output(style, seeded_retrieval_results):
    from retrieval.citations.builder import CitationBuilder
    from retrieval.citations.base import CitationStyle

    builder = CitationBuilder(style=CitationStyle[style])
    results = seeded_retrieval_results["docs"]
    annotated = builder.build(answer="Test answer about authentication.", results=results)

    assert annotated is not None, f"Builder returned None for style {style}"
    # AnnotatedAnswer has .answer, .citations, .sources
    assert annotated.answer, f"Answer text is empty for style {style}"
    assert len(annotated.citations) == len(results), "Must produce one citation per result"
    for citation in annotated.citations:
        assert citation.source, f"Citation source is empty for style {style}"
