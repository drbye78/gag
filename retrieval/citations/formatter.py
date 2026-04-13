from typing import List
from retrieval.citations.base import CitationSource, CitationStyle


class CitationFormatter:
    @staticmethod
    def format(
        answer: str,
        sources: List[CitationSource],
        style: CitationStyle,
    ) -> str:
        if style == CitationStyle.VERBATIM:
            return CitationFormatter._verbatim(answer, sources)
        elif style == CitationStyle.PARENTHETICAL:
            return CitationFormatter._parenthetical(answer, sources)
        elif style == CitationStyle.FOOTNOTE:
            return CitationFormatter._footnote(answer, sources)
        elif style == CitationStyle.HIGHLIGHT:
            return CitationFormatter._highlight(answer, sources)
        return answer

    @staticmethod
    def _verbatim(answer: str, sources: List[CitationSource]) -> str:
        parts = [answer, "\n\nSources:"]
        for i, src in enumerate(sources, 1):
            parts.append(f"[{i}] {src.source_name}: {src.content[:300]}...")
        return "\n".join(parts)

    @staticmethod
    def _parenthetical(answer: str, sources: List[CitationSource]) -> str:
        citation_ids = f"[{', '.join(str(i + 1) for i in range(len(sources)))}]"
        return f"{answer} (see {citation_ids})"

    @staticmethod
    def _footnote(answer: str, sources: List[CitationSource]) -> str:
        citations = " ".join(f"[{i + 1}]" for i in range(len(sources)))
        return f"{answer} {citations}"

    @staticmethod
    def _highlight(answer: str, sources: List[CitationSource]) -> str:
        parts = [answer, "\n\n**Sources:**"]
        for i, src in enumerate(sources, 1):
            parts.append(f"- [{src.source_name}](#source-{i})")
        return "\n".join(parts)
