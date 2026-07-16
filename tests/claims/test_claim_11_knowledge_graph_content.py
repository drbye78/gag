"""
README claim: "Use Cases: 7 pre-built use cases per platform; ADRs: 5 architecture decision records;
Reference Architectures: 8 reference architectures"
Source: README.md lines 74-76
"""
import pytest


@pytest.mark.claim
def test_use_cases_per_platform():
    from core.knowledge.usecases import get_use_case_library
    lib = get_use_case_library()
    platforms = ["sap_btp", "aws", "azure", "gcp", "tanzu", "powerplatform"]
    for platform in platforms:
        use_cases = lib.get_by_platform(platform) if hasattr(lib, "get_by_platform") else []
        assert len(use_cases) >= 7, f"Platform {platform} has {len(use_cases)} use cases, need 7"
        for uc in use_cases:
            name = getattr(uc, "name", "") or (uc.get("name", "") if isinstance(uc, dict) else "")
            desc = getattr(uc, "description", "") or (uc.get("description", "") if isinstance(uc, dict) else "")
            assert name and len(name) > 3, f"Use case name is placeholder: {name}"
            assert desc and len(desc) > 20, f"Use case description is placeholder: {desc}"


@pytest.mark.claim
def test_adrs_count():
    from core.knowledge.adrs import get_adr_library
    lib = get_adr_library()
    adrs = lib.get_all() if hasattr(lib, "get_all") else []
    assert len(adrs) >= 5, f"Expected 5 ADRs, got {len(adrs)}"
    for adr in adrs:
        title = getattr(adr, "title", "") or (adr.get("title", "") if isinstance(adr, dict) else "")
        assert title and len(title) > 5, f"ADR title is placeholder: {title}"


@pytest.mark.claim
def test_reference_architectures_count():
    from core.knowledge.reference import get_reference_library
    lib = get_reference_library()
    refs = lib.get_all() if hasattr(lib, "get_all") else []
    assert len(refs) >= 8, f"Expected 8 reference architectures, got {len(refs)}"
    for ref in refs:
        name = getattr(ref, "name", "") or (ref.get("name", "") if isinstance(ref, dict) else "")
        assert name and len(name) > 3, f"Reference architecture name is placeholder: {name}"
