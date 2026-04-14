"""Evaluation test suite for UI sketch understanding.

Tests end-to-end: sketch ingestion → extraction → graph → retrieval → suggestion.
Uses sample images in evaluation/samples/.
Skipped if no sample images present or VLM API keys not configured.
"""

import os
import pytest

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "samples")


class UITestCase:
    def __init__(self, sketch_path, expected_elements, expected_sap_candidates, min_score=0.7):
        self.sketch_path = sketch_path
        self.expected_elements = expected_elements
        self.expected_sap_candidates = expected_sap_candidates
        self.min_acceptable_score = min_score


# Define test cases
TEST_CASES = [
    UITestCase(
        sketch_path=os.path.join(SAMPLES_DIR, "table_with_filter.png"),
        expected_elements=[
            {"type": "table", "label": None},
            {"type": "filter", "label": None},
            {"type": "button", "label": None},
        ],
        expected_sap_candidates=["sap.m.Table", "sap.ui.comp.filterbar.FilterBar"],
        min_acceptable_score=0.7,
    ),
    UITestCase(
        sketch_path=os.path.join(SAMPLES_DIR, "form_page.png"),
        expected_elements=[
            {"type": "form", "label": None},
            {"type": "input", "label": None},
            {"type": "button", "label": None},
        ],
        expected_sap_candidates=["sap.ui.layout.form.SimpleForm", "sap.m.Input", "sap.m.Button"],
        min_acceptable_score=0.7,
    ),
]


def _compute_element_f1(extracted, expected):
    """Compute F1 score for element detection."""
    if not expected:
        return 1.0 if not extracted else 0.0

    true_positives = sum(
        1 for exp in expected
        if any(ext.get("type") == exp["type"] for ext in extracted)
    )

    precision = true_positives / len(extracted) if extracted else 0.0
    recall = true_positives / len(expected)
    return 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0


@pytest.mark.skipif(
    not os.path.exists(SAMPLES_DIR) or not os.listdir(SAMPLES_DIR),
    reason="No sample images in evaluation/samples/"
)
@pytest.mark.parametrize("test_case", TEST_CASES, ids=[tc.sketch_path for tc in TEST_CASES])
def test_ui_understanding(test_case):
    """End-to-end test."""
    pytest.importorskip("ui.vlm_extractor")
    import asyncio
    from ui.vlm_extractor import VLMUIExtractor
    from ui.evidence_aggregator import EvidenceAggregator
    from ui.sap_knowledge import get_sap_catalog

    async def run_test():
        extractor = VLMUIExtractor()
        image_url = f"file://{test_case.sketch_path}"
        vlm_schema = await extractor.extract(image_url)

        if vlm_schema is None:
            pytest.fail("VLM extraction returned None")

        aggregator = EvidenceAggregator()
        result = aggregator.aggregate(image_url=image_url, vlm_schema=vlm_schema)

        extracted = [{"type": e.element_type, "label": e.label} for e in result.elements]
        f1 = _compute_element_f1(extracted, test_case.expected_elements)
        assert f1 >= test_case.min_acceptable_score, (
            f"Element F1 score {f1} below threshold {test_case.min_acceptable_score}"
        )

        catalog = get_sap_catalog()
        all_candidates = []
        for elem in result.elements:
            candidates = catalog.find_for_element_type(elem.element_type)
            all_candidates.extend(c.name for c in candidates)

        for expected_sap in test_case.expected_sap_candidates:
            assert expected_sap in all_candidates, (
                f"Expected SAP component {expected_sap} not found in candidates"
            )

    asyncio.run(run_test())
