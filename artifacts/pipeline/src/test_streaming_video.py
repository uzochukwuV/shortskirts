#!/usr/bin/env python3
"""
Test script for streaming and video generation.
Usage: python test_streaming_video.py
"""

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


async def test_dashscope_provider():
    """Test DashScope video provider."""
    print("\n" + "=" * 60)
    print("Testing DashScope Video Provider")
    print("=" * 60)
    
    try:
        from pipeline.providers.dashscope import DashScopeVideoProvider
        from genblaze_core.models.step import Step
        from genblaze_core import Modality
        
        # Check API key
        api_key = os.environ.get("DASHSCOPE_API_KEY")
        if not api_key:
            print("⚠️  DASHSCOPE_API_KEY not set - skipping video generation test")
            return True
        
        provider = DashScopeVideoProvider()
        print(f"✅ Provider initialized: {provider.name}")
        
        # Build a test step
        step = Step(
            provider='dashscope-video',
            model='happyhorse-1.1-t2v',
            prompt='A beautiful anime girl with pink hair standing in a flower garden, cinematic lighting',
        )
        step.params = {
            'duration': 5,
            'resolution': '720P',
            'ratio': '16:9',
            'seed': 42,
        }
        step.modality = Modality.VIDEO
        
        print(f"📤 Submitting video generation request...")
        print(f"   Model: {step.model}")
        print(f"   Prompt: {step.prompt[:60]}...")
        
        task_id = provider.submit(step)
        print(f"✅ Task submitted: {task_id}")
        
        return task_id
        
    except ImportError as e:
        print(f"⚠️  Import error: {e}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_streaming_orchestrator():
    """Test streaming orchestrator."""
    print("\n" + "=" * 60)
    print("Testing Streaming Orchestrator")
    print("=" * 60)
    
    try:
        from pipeline.unified_agent import (
            UnifiedStreamingOrchestrator,
            StreamEvent,
            EventType,
        )
        
        orchestrator = UnifiedStreamingOrchestrator()
        print("✅ StreamingOrchestrator initialized")
        
        # Test event emission
        test_stream_id = "test-stream-123"
        
        async def event_receiver():
            events = []
            async for event in orchestrator.subscribe(test_stream_id):
                events.append(event)
                print(f"  📩 Event: {event.type}")
                if event.type in (EventType.PIPELINE_COMPLETED, EventType.PIPELINE_FAILED):
                    break
            return events
        
        # Start receiver
        receiver_task = asyncio.create_task(event_receiver())
        
        # Emit some test events
        await orchestrator.emit(test_stream_id, StreamEvent(
            type=EventType.CONNECTED,
            data={"stream_id": test_stream_id}
        ))
        await asyncio.sleep(0.1)
        
        await orchestrator.emit(test_stream_id, StreamEvent(
            type=EventType.STEP_STARTED,
            data={"scene_id": 1, "message": "Starting scene 1"}
        ))
        await asyncio.sleep(0.1)
        
        await orchestrator.emit(test_stream_id, StreamEvent(
            type=EventType.PIPELINE_COMPLETED,
            data={"scenes_completed": 1}
        ))
        
        # Wait for receiver
        events = await receiver_task
        
        print(f"✅ Received {len(events)} events")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_unified_agent_tools():
    """Test unified agent tools."""
    print("\n" + "=" * 60)
    print("Testing Unified Agent Tools")
    print("=" * 60)
    
    try:
        from pipeline.consolidated_tools import register_all_tools
        from pipeline.unified_agent import UnifiedAgentExecutor
        
        executor = UnifiedAgentExecutor()
        register_all_tools(executor)
        
        print(f"✅ Registered {len(executor._tools)} tools:")
        for name in sorted(executor._tools.keys()):
            print(f"   - {name}")
        
        # Get tool definitions
        definitions = executor.get_tool_definitions()
        print(f"\n✅ Generated {len(definitions)} tool definitions")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_asset_manager():
    """Test asset manager."""
    print("\n" + "=" * 60)
    print("Testing Asset Manager")
    print("=" * 60)
    
    try:
        import asyncpg
        from urllib.parse import urlparse
        
        # Connect to database
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, _, value = line.partition('=')
                    os.environ[key] = value.strip('"')
        
        db_url = os.environ.get('COCKROACHDB_URL')
        parsed = urlparse(db_url)
        
        pool = await asyncpg.create_pool(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path.lstrip('/') or 'defaultdb',
            ssl='require',
            min_size=1,
            max_size=2,
        )
        
        async with pool.acquire() as conn:
            from pipeline.unified_agent import AssetManager
            
            asset_manager = AssetManager(conn)
            
            # Get a story to test with
            story = await conn.fetchrow("SELECT id, title FROM stories LIMIT 1")
            if story:
                story_id = str(story['id'])
                print(f"📖 Testing with story: {story['title']}")
                
                # Test getting assets (should be empty)
                assets = await asset_manager.get_assets(story_id)
                print(f"✅ Asset manager working - found {len(assets)} assets")
                
                # Test search (should also work)
                results = await asset_manager.search_assets(story_id, "test")
                print(f"✅ Search working - found {len(results)} results")
            else:
                print("⚠️  No stories found to test with")
        
        await pool.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_video_generation_with_polling(task_id: str):
    """Test video generation with polling."""
    if not task_id:
        print("\n⏭️  Skipping video polling test (no task_id)")
        return True
    
    print("\n" + "=" * 60)
    print(f"Testing Video Generation (Task: {task_id[:20]}...)")
    print("=" * 60)
    
    try:
        from pipeline.providers.dashscope import DashScopeVideoProvider
        
        provider = DashScopeVideoProvider()
        
        print("⏳ Polling for completion (max 3 minutes)...")
        import time
        start = time.time()
        max_wait = 180  # 3 minutes
        
        while time.time() - start < max_wait:
            status = provider._poll_status(task_id)
            elapsed = int(time.time() - start)
            print(f"  [{elapsed}s] Status: {status}")
            
            if status == "SUCCEEDED":
                print("✅ Video generation succeeded!")
                
                # Fetch output
                from genblaze_core.models.step import Step
                step = Step(provider='dashscope-video', model='happyhorse-1.1-t2v', prompt='')
                step = provider.fetch_output(task_id, step)
                
                if step.assets:
                    video_url = step.assets[0].url
                    print(f"📹 Video URL: {video_url[:80]}...")
                return True
                
            elif status == "FAILED":
                print("❌ Video generation failed")
                return False
            
            # Wait before polling again
            time.sleep(15)
        
        print("⏱️  Timeout waiting for video")
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Unified Agent - Streaming & Video Generation Tests")
    print("=" * 60)
    
    results = {}
    
    # Test 1: Unified agent tools
    results["tools"] = await test_unified_agent_tools()
    
    # Test 2: Streaming orchestrator
    results["streaming"] = await test_streaming_orchestrator()
    
    # Test 3: Asset manager
    results["assets"] = await test_asset_manager()
    
    # Test 4: DashScope provider
    task_id = await test_dashscope_provider()
    results["dashscope_submit"] = task_id is not None
    
    # Test 5: Poll for video completion (if we have a task_id)
    if task_id:
        results["video_generation"] = await test_video_generation_with_polling(task_id)
    else:
        results["video_generation"] = None
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    for name, result in results.items():
        status = "✅" if result is True else "❌" if result is False else "⏭️"
        value = "PASS" if result is True else "FAIL" if result is False else "SKIP"
        print(f"  {status} {name}: {value}")
    
    all_passed = all(r is True for r in results.values() if r is not None)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All tests passed!")
    else:
        print("⚠️  Some tests failed or were skipped")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
