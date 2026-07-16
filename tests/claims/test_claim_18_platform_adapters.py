"""
README claim: "Platform Adapters: SAP BTP, VMware Tanzu, Power Platform, AWS, Azure, GCP (extensible)"
Source: README.md line 70
"""
import pytest


@pytest.mark.claim
@pytest.mark.parametrize("platform", ["sap", "tanzu", "powerplatform", "aws", "azure", "gcp"])
def test_platform_adapter_exists(platform):
    from core.adapters import get_adapter_registry
    registry = get_adapter_registry()

    # Try to register all adapters
    try:
        from core.adapters.sap import SAPBTPAdapter
        if "sap" not in registry.list_platforms():
            registry.register(SAPBTPAdapter())
    except Exception:
        pass
    try:
        from core.adapters.tanzu import TanzuAdapter
        if "tanzu" not in registry.list_platforms():
            registry.register(TanzuAdapter())
    except Exception:
        pass
    try:
        from core.adapters.powerplatform import PowerPlatformAdapter
        if "powerplatform" not in registry.list_platforms():
            registry.register(PowerPlatformAdapter())
    except Exception:
        pass
    try:
        from core.adapters.clouds import AWSAdapter, AzureAdapter, GCPAdapter
        if "aws" not in registry.list_platforms():
            registry.register(AWSAdapter())
        if "azure" not in registry.list_platforms():
            registry.register(AzureAdapter())
        if "gcp" not in registry.list_platforms():
            registry.register(GCPAdapter())
    except Exception:
        pass

    platforms = registry.list_platforms()
    assert platform in platforms, f"Platform '{platform}' not in registry: {platforms}"


@pytest.mark.claim
@pytest.mark.asyncio
async def test_aws_adapter_produces_non_hardcoded_recommendations():
    from core.adapters.clouds import AWSAdapter
    from core.adapters.base import AdapterInput
    from models.ir import IRFeature, PlatformContext

    adapter = AWSAdapter()

    # Create two different IRs with different feature flags
    ir1 = IRFeature(has_serverless=True, has_api=True)  # serverless API
    ir2 = IRFeature(has_container=True, has_microservices=True)  # container microservices

    ctx = PlatformContext(platform="aws", environment="test", region="us-east-1")
    input1 = AdapterInput(ir_features=ir1, platform_context=ctx)
    input2 = AdapterInput(ir_features=ir2, platform_context=ctx)

    # transform_ir_to_platform is sync (not async) — do not await
    output1 = adapter.transform_ir_to_platform(input1)
    output2 = adapter.transform_ir_to_platform(input2)

    # Outputs should differ based on input features
    assert output1.recommendations != output2.recommendations, \
        "AWS adapter returns same recommendations for different inputs -- likely hardcoded"
