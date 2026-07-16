"""
README claim: "Vision Language Model (VLM) processor for architecture diagrams;
Supports Qwen Vision and OpenAI vision providers"
Source: README.md lines 103-104
"""
import pytest
import inspect


@pytest.mark.claim
def test_vlm_processor_exists():
    from multimodal.vlm import VLMProcessor
    assert VLMProcessor is not None


@pytest.mark.claim
def test_vlm_supports_qwen_and_openai():
    from multimodal.vlm import VLMProcessor
    source = inspect.getsource(VLMProcessor)
    assert "qwen" in source.lower(), "VLM processor does not support Qwen Vision"
    assert "openai" in source.lower(), "VLM processor does not support OpenAI vision"


@pytest.mark.claim
def test_vlm_no_fire_and_forget():
    from multimodal import ir_builder
    source = inspect.getsource(ir_builder)
    # Fire-and-forget is: loop.create_task(coro) without storing/awaiting the result
    if "loop.create_task" in source:
        # Must be followed by await or stored in a variable
        lines = source.split("\n")
        for i, line in enumerate(lines):
            if "loop.create_task" in line and "await" not in line:
                # Check if the result is stored
                if "=" not in line.split("loop.create_task")[0]:
                    pytest.fail("ir_builder uses fire-and-forget create_task without await or storage")
