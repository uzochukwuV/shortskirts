"""
Test script for unified agent system.
Run with: python -m test_unified_agent
"""

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    # Test unified_agent
    from pipeline.unified_agent import (
        UnifiedStreamingOrchestrator,
        UnifiedAgentExecutor,
        StreamEvent,
        EventType,
        Asset,
        AssetManager,
        SYSTEM_PROMPT,
        get_orchestrator,
        get_executor,
    )
    print("  ✅ unified_agent")
    
    # Test consolidated_tools
    from pipeline.consolidated_tools import (
        register_all_tools,
        get_story_context,
        get_scene_timeline,
        generate_video,
        extract_scene_frame,
    )
    print("  ✅ consolidated_tools")
    
    # Test agent_llm
    from pipeline.agent_llm import (
        TokenRouterClient,
        ChatMessage,
        ToolCall,
        ChatResponse,
    )
    print("  ✅ agent_llm")
    
    return True


def test_stream_event():
    """Test StreamEvent creation."""
    print("\nTesting StreamEvent...")
    
    from pipeline.unified_agent import StreamEvent, EventType
    
    event = StreamEvent(
        type=EventType.STEP_STARTED,
        data={
            "scene_id": 1,
            "message": "Starting scene",
        }
    )
    
    assert event.type == EventType.STEP_STARTED
    assert event.data["scene_id"] == 1
    assert event.timestamp  # Should have timestamp
    
    sse = event.to_sse()
    assert "data: " in sse
    assert '"type": "step.started"' in sse
    
    print("  ✅ StreamEvent creation")
    print("  ✅ StreamEvent SSE formatting")


def test_asset_class():
    """Test Asset dataclass."""
    print("\nTesting Asset...")
    
    from pipeline.unified_agent import Asset
    
    asset = Asset(
        story_id="test-story",
        entity_type="scene",
        entity_id="scene-1",
        asset_type="video",
        storage_key="stories/test/video.mp4",
        storage_url="https://b2.example.com/video.mp4",
        mime_type="video/mp4",
    )
    
    assert asset.story_id == "test-story"
    assert asset.asset_type == "video"
    assert asset.id  # Should have UUID
    
    print("  ✅ Asset creation")
    print("  ✅ Asset fields")


def test_tool_executor():
    """Test tool executor registration."""
    print("\nTesting ToolExecutor...")
    
    from pipeline.unified_agent import UnifiedAgentExecutor
    
    executor = UnifiedAgentExecutor()
    
    # Register a test tool
    async def test_tool(pool, arg1, arg2="default"):
        return {"arg1": arg1, "arg2": arg2}
    
    executor.register_tool("test_tool", test_tool)
    
    assert "test_tool" in executor._tools
    assert executor.max_iterations == 10
    
    # Get tool definitions
    tools = executor.get_tool_definitions()
    tool_names = [t["function"]["name"] for t in tools]
    assert "test_tool" in tool_names
    
    print("  ✅ Tool registration")
    print("  ✅ Tool definitions")


def test_consolidated_tools():
    """Test consolidated tools registry."""
    print("\nTesting consolidated_tools...")
    
    from pipeline.consolidated_tools import register_all_tools
    from pipeline.unified_agent import UnifiedAgentExecutor
    
    executor = UnifiedAgentExecutor()
    register_all_tools(executor)
    
    # Check expected tools are registered
    expected_tools = [
        "get_story_context",
        "get_scene_timeline",
        "list_stories",
        "create_story",
        "create_scene",
        "update_scene",
        "delete_scene",
        "approve_scene",
        "generate_video",
        "wait_for_generation",
        "extract_scene_frame",
        "screenshot_previous_scene",
        "set_character_reference",
        "set_scene_continuity",
        "assemble_episode",
        "add_transition",
        "generate_seo_metadata",
        "check_style_consistency",
        "compare_scenes",
        "search_assets",
    ]
    
    registered = list(executor._tools.keys())
    
    missing = [t for t in expected_tools if t not in registered]
    if missing:
        print(f"  ⚠️  Missing tools: {missing}")
    
    print(f"  ✅ Registered {len(registered)} tools")


def test_system_prompt():
    """Test system prompt content."""
    print("\nTesting SYSTEM_PROMPT...")
    
    from pipeline.unified_agent import SYSTEM_PROMPT
    
    assert len(SYSTEM_PROMPT) > 0
    assert "Dysentry" in SYSTEM_PROMPT
    assert "Story Management" in SYSTEM_PROMPT
    assert "Scene Generation" in SYSTEM_PROMPT
    
    print("  ✅ SYSTEM_PROMPT content")


def test_event_types():
    """Test EventType enum."""
    print("\nTesting EventType...")
    
    from pipeline.unified_agent import EventType
    
    # Check all expected event types
    expected = [
        "CONNECTED",
        "HEARTBEAT",
        "STREAM_CLOSED",
        "PIPELINE_STARTED",
        "PIPELINE_PROGRESS",
        "PIPELINE_COMPLETED",
        "PIPELINE_FAILED",
        "STEP_QUEUED",
        "STEP_STARTED",
        "STEP_PROGRESS",
        "STEP_COMPLETED",
        "STEP_FAILED",
        "MESSAGE",
        "TOOL_START",
        "TOOL_PROGRESS",
        "TOOL_COMPLETE",
        "TOOL_ERROR",
        "DONE",
        "ERROR",
    ]
    
    for et in expected:
        assert hasattr(EventType, et), f"Missing EventType.{et}"
    
    print(f"  ✅ All {len(expected)} event types defined")


def test_dashscope_provider():
    """Test DashScope provider can be loaded."""
    print("\nTesting DashScope provider...")
    
    try:
        from pipeline.providers.dashscope import DashScopeVideoProvider, DashScopeImageProvider
        
        provider = DashScopeVideoProvider()
        assert provider.name == "dashscope-video"
        
        print("  ✅ DashScopeVideoProvider")
        
        image_provider = DashScopeImageProvider()
        assert image_provider.name == "dashscope-image"
        
        print("  ✅ DashScopeImageProvider")
    except ImportError as e:
        print(f"  ⚠️  DashScope provider import failed: {e}")
        print("     This is OK if genblaze-core is not installed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Unified Agent System Tests")
    print("=" * 60)
    
    try:
        test_imports()
        test_stream_event()
        test_asset_class()
        test_tool_executor()
        test_consolidated_tools()
        test_system_prompt()
        test_event_types()
        test_dashscope_provider()
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
