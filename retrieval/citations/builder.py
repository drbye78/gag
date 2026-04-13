import re
from typing import List, Dict, Any, Optional

from retrieval.citations.base import (
    CitationSource,
    Citation,
    AnnotatedAnswer,
    CitationStyle,
)


class CitationBuilder:
    def __init__(
        self,
        style: CitationStyle = CitationStyle.PARENTHETICAL,
        max_citations: int = 10,
    ):
        self.style = style
        self.max_citations = max_citations

    def build(
        self,
        answer: str,
        results: List[Dict[str, Any]],
    ) -> AnnotatedAnswer:
        sources = self._build_sources(results)
        citations = self._create_citations(sources)
        formatted_answer = self._format_answer(answer, citations, sources)

        return AnnotatedAnswer(
            answer=formatted_answer,
            citations=citations,
            sources=sources,
            style=self.style,
            metadata={"source_count": len(sources)},
        )

    def _build_sources(
        self,
        results: List[Dict[str, Any]],
    ) -> List[CitationSource]:
        sources = []
        for i, r in enumerate(results[: self.max_citations]):
            sources.append(
                CitationSource(
                    source_id=str(i + 1),
                    content=r.get("content", ""),
                    source_type=r.get("source", "unknown"),
                    source_name=r.get("source_name", r.get("source", "source")),
                    url=r.get("url"),
                    line_start=r.get("line_start"),
                    line_end=r.get("line_end"),
                    page=r.get("page"),
                    chunk_index=r.get("chunk_index"),
                    score=r.get("score", 0.0),
                    metadata=r.get("metadata", {}),
                )
            )
        return sources

    def _create_citations(
        self,
        sources: List[CitationSource],
    ) -> List[Citation]:
        return [
            Citation(
                id=src.source_id,
                source=src,
                spans=[],
                confidence=src.score,
            )
            for src in sources
        ]

    def _format_answer(
        self,
        answer: str,
        citations: List[Citation],
        sources: List[CitationSource],
    ) -> str:
        if self.style == CitationStyle.PARENTHETICAL:
            if sources:
                citation_ids = f"[{', '.join(s.source_id for s in sources)}]"
                return f"{answer} (see {citation_ids})"
        elif self.style == CitationStyle.FOOTNOTE:
            if sources:
                citation_ids = " ".join(f"[{s.source_id}]" for s in sources)
                return f"{answer} {citation_ids}"
        elif self.style == CitationStyle.VERBATIM:
            return answer
        elif self.style == CitationStyle.HIGHLIGHT:
            return answer

        return answer
