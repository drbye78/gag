from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import re


class CrossRefType(str, Enum):
    MARKDOWN_LINK = "markdown_link"
    HTML_LINK = "html_link"
    URL = "url"
    DOCUMENT_ID = "document_id"
    CODE_REF = "code_ref"
    SECTION_REF = "section_ref"
    CITATION = "citation"


@dataclass
class CrossReference:
    ref_type: CrossRefType
    source_id: str
    target_id: str
    target_text: str
    context: str
    line_number: int = 0


@dataclass
class CrossRefResult:
    source_id: str
    references: List[CrossReference]
    total_refs: int
    took_ms: int


class CrossReferenceExtractor:
    def extract(self, text: str, source_id: str) -> CrossRefResult:
        import time

        start = time.time()

        references = []
        references.extend(self._extract_markdown_links(text, source_id))
        references.extend(self._extract_html_links(text, source_id))
        references.extend(self._extract_urls(text, source_id))
        references.extend(self._extract_document_ids(text, source_id))
        references.extend(self._extract_code_refs(text, source_id))
        references.extend(self._extract_section_refs(text, source_id))

        took = int((time.time() - start) * 1000)
        return CrossRefResult(
            source_id=source_id,
            references=references,
            total_refs=len(references),
            took_ms=took,
        )

    def _extract_markdown_links(
        self, text: str, source_id: str
    ) -> List[CrossReference]:
        refs = []
        pattern = r"\[([^\]]+)\]\(([^)]+)\)"

        for match in re.finditer(pattern, text):
            link_text = match.group(1)
            link_url = match.group(2)
            line = text[: match.start()].count("\n") + 1

            target_id = self._normalize_target(link_url)
            if target_id:
                refs.append(
                    CrossReference(
                        ref_type=CrossRefType.MARKDOWN_LINK,
                        source_id=source_id,
                        target_id=target_id,
                        target_text=link_text,
                        context=self._get_context(text, match.start()),
                        line_number=line,
                    )
                )

        return refs

    def _extract_html_links(self, text: str, source_id: str) -> List[CrossReference]:
        refs = []
        pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]*)</a>'

        for match in re.finditer(pattern, text, re.IGNORECASE):
            link_url = match.group(1)
            link_text = match.group(2)
            line = text[: match.start()].count("\n") + 1

            target_id = self._normalize_target(link_url)
            if target_id:
                refs.append(
                    CrossReference(
                        ref_type=CrossRefType.HTML_LINK,
                        source_id=source_id,
                        target_id=target_id,
                        target_text=link_text,
                        context=self._get_context(text, match.start()),
                        line_number=line,
                    )
                )

        return refs

    def _extract_urls(self, text: str, source_id: str) -> List[CrossReference]:
        refs = []
        pattern = r'https?://[^\s\)"\']+'

        for match in re.finditer(pattern, text):
            url = match.group(0)
            line = text[: match.start()].count("\n") + 1

            if self._is_internal_url(url):
                refs.append(
                    CrossReference(
                        ref_type=CrossRefType.URL,
                        source_id=source_id,
                        target_id=url,
                        target_text=url,
                        context=self._get_context(text, match.start()),
                        line_number=line,
                    )
                )

        return refs

    def _extract_document_ids(self, text: str, source_id: str) -> List[CrossReference]:
        refs = []
        patterns = [
            r"DOC[-_]?\d+",
            r"REF[-_]?\d+",
            r"[A-Z]{2,}-\d+",
            r"#([a-zA-Z0-9_-]+)",
            r"§\d+(\.\d+)*",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text):
                doc_id = match.group(0)
                line = text[: match.start()].count("\n") + 1

                refs.append(
                    CrossReference(
                        ref_type=CrossRefType.DOCUMENT_ID,
                        source_id=source_id,
                        target_id=doc_id,
                        target_text=doc_id,
                        context=self._get_context(text, match.start()),
                        line_number=line,
                    )
                )

        return refs

    def _extract_code_refs(self, text: str, source_id: str) -> List[CrossReference]:
        refs = []
        patterns = [
            (r"from\s+([a-zA-Z_][a-zA-Z0-9_.]*)", "import"),
            (r"import\s+([a-zA-Z_][a-zA-Z0-9_.]*)", "import"),
            (r'require\(["\']([^"\']+)["\']\)', "require"),
            (r"include::([^\[]+)\[\]", "include"),
            (r'@import\s+["\']?([^"\';\s]+)', "scss"),
        ]

        for pattern, ref_type in patterns:
            for match in re.finditer(pattern, text):
                module_ref = match.group(1)
                line = text[: match.start()].count("\n") + 1

                refs.append(
                    CrossReference(
                        ref_type=CrossRefType.CODE_REF,
                        source_id=source_id,
                        target_id=f"module:{module_ref}",
                        target_text=module_ref,
                        context=self._get_context(text, match.start()),
                        line_number=line,
                    )
                )

        return refs

    def _extract_section_refs(self, text: str, source_id: str) -> List[CrossReference]:
        refs = []
        patterns = [
            r"see\s+section\s+([\d.]+)",
            r"section\s+([\d.]+)",
            r"chapter\s+(\d+)",
            r"appendix\s+([A-Z])",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                section_ref = match.group(0)
                line = text[: match.start()].count("\n") + 1

                refs.append(
                    CrossReference(
                        ref_type=CrossRefType.SECTION_REF,
                        source_id=source_id,
                        target_id=f"section:{section_ref}",
                        target_text=section_ref,
                        context=self._get_context(text, match.start()),
                        line_number=line,
                    )
                )

        return refs

    def _normalize_target(self, url: str) -> Optional[str]:
        if not url or url.startswith("#"):
            return None

        if url.startswith("http"):
            return url

        if url.startswith("/"):
            return url.lstrip("/")

        if url.endswith(".md") or url.endswith(".html"):
            return url.rsplit(".", 1)[0]

        return url

    def _is_internal_url(self, url: str) -> bool:
        internal_domains = ["localhost", "internal", "company.com"]
        return any(domain in url.lower() for domain in internal_domains)

    def _get_context(self, text: str, position: int, context_size: int = 50) -> str:
        start = max(0, position - context_size)
        end = min(len(text), position + context_size)
        return text[start:end].replace("\n", " ")


def get_cross_reference_extractor() -> CrossReferenceExtractor:
    return CrossReferenceExtractor()
