"""
README claim: "Code chunking with entity extraction (Python, JavaScript, TypeScript, Go, Rust, Java, Kotlin)"
Source: README.md line 121
"""
import pytest


@pytest.mark.claim
@pytest.mark.parametrize("language,ext,code_snippet", [
    ("python", ".py", "def foo():\n    return 1\n\nclass Bar:\n    pass"),
    ("javascript", ".js", "function foo() { return 1; }\nclass Bar {}"),
    ("typescript", ".ts", "function foo(): number { return 1; }\nclass Bar {}"),
    ("go", ".go", "func foo() int { return 1 }"),
    ("rust", ".rs", "fn foo() -> i32 { 1 }"),
    ("java", ".java", "public class Bar { public int foo() { return 1; } }"),
    ("kotlin", ".kt", "fun foo(): Int { return 1 }\nclass Bar"),
])
def test_code_chunker_extracts_entities(language, ext, code_snippet):
    from ingestion.chunker import CodeChunker
    chunker = CodeChunker()
    result = chunker.chunk_file(f"test{ext}", code_snippet)
    assert len(result.chunks) > 0, f"Code chunker produced 0 chunks for {language}"
    has_entity = any(c.metadata.get("entity_type") for c in result.chunks)
    assert has_entity, f"Code chunker did not extract any entities for {language}"
