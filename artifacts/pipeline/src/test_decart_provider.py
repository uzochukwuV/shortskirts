#!/usr/bin/env python3
"""
Test script for Decart provider via the provider router.

Usage: python test_decart_provider.py
"""

import asyncio
import os
import sys
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Load environment - check multiple locations
env_paths = [
    os.path.join(os.path.dirname(__file__), ".env"),
    os.path.join(os.path.dirname(__file__), "..", ".env"),
    os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
]

for env_path in env_paths:
    if os.path.exists(env_path):
        print(f"Loading env from: {env_path}")
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, _, value = line.partition("=")
                    os.environ[key] = value.strip('"')
        break


def test_provider_router():
    """Test the provider router initialization."""
    print("\n" + "=" * 60)
    print("Testing Provider Router")
    print("=" * 60)
    
    from pipeline.providers import get_router, ProviderType, VideoProviderRouter
    
    # Create router
    router = VideoProviderRouter()
    
    # Get status
    status = router.get_status_summary()
    print(f"\nProvider Status:")
    for name, info in status["providers"].items():
        enabled = "✅" if info["enabled"] else "❌"
        has_key = "🔑" if info["has_api_key"] else "🔒"
        priority = info["priority"]
        print(f"  {enabled} {has_key} {name:<12} (priority: {priority})")
    
    print(f"\nAvailable providers: {[p.value for p in router.available_providers]}")
    
    return router


def test_decart_provider(router):
    """Test Decart provider directly."""
    print("\n" + "=" * 60)
    print("Testing Decart Video Provider")
    print("=" * 60)
    
    from genblaze_core.models.step import Step
    from genblaze_core import Modality
    from pipeline.providers import ProviderType
    from decart.models import _MODELS
    
    # Check if Decart is available
    if ProviderType.DECART not in router.available_providers:
        print("❌ Decart not available")
        return None
    
    # Get Decart provider
    provider = router.get_provider(ProviderType.DECART)
    print(f"✅ Using provider: {provider.name}")
    
    # Check API key
    api_key = os.environ.get("DECART_API_KEY", "")
    if api_key:
        masked = f"{api_key[:8]}...{api_key[-4:]}"
        print(f"🔑 API key: {masked}")
    
    # List available models
    print("\n📋 Available Decart video models:")
    for name, model in _MODELS.get('video', {}).items():
        if model:
            schema = model.input_schema.__name__ if model.input_schema else 'N/A'
            print(f"   - {name}: {schema}")
    
    print("\n⚠️  Note: Decart Lucy models are primarily video-editing models")
    print("   They require a 'data' video file input, not text-to-video.")
    print("   For text-to-video, use DashScope instead.")
    
    # Try to submit with lucy-latest
    # Note: This will fail because it requires video input data
    step = Step(
        provider="decart",
        model="lucy-latest",
        prompt="A beautiful anime girl with pink hair standing in a flower garden",
        modality=Modality.VIDEO,
    )
    step.params = {
        "duration": 5,
        "resolution": "720p",
    }
    
    print(f"\n📤 Attempting to submit (will likely need video input)...")
    print(f"   Model: {step.model}")
    print(f"   Prompt: {step.prompt[:60]}...")
    
    try:
        task_id = provider.submit(step)
        print(f"✅ Task submitted: {task_id}")
        return task_id, provider
    except Exception as e:
        error_msg = str(e)
        if "data" in error_msg.lower() or "required" in error_msg.lower():
            print(f"⚠️  Expected error (Decart requires video input):")
            print(f"   {error_msg[:200]}...")
        else:
            print(f"❌ Submit failed: {error_msg}")
        return None


def test_generate_video_convenience():
    """Test the generate_video convenience function."""
    print("\n" + "=" * 60)
    print("Testing generate_video() Convenience Function")
    print("=" * 60)
    
    from pipeline.providers import generate_video, ProviderType
    
    try:
        print("📤 Generating video with Decart...")
        
        video_url, task_id, provider_name = generate_video(
            prompt="A serene mountain landscape at sunset with birds flying, cinematic",
            provider_type=ProviderType.DECART,
            duration=5,
        )
        
        print(f"✅ Video generated!")
        print(f"   URL: {video_url[:80]}...")
        print(f"   Task ID: {task_id}")
        print(f"   Provider: {provider_name}")
        
        return video_url
        
    except Exception as e:
        print(f"❌ Generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def poll_for_completion(router, task_id, provider_name, max_wait=300):
    """Poll for video completion."""
    print("\n" + "=" * 60)
    print(f"Polling for Completion (max {max_wait}s)")
    print("=" * 60)
    
    start = time.time()
    poll_count = 0
    
    while time.time() - start < max_wait:
        elapsed = int(time.time() - start)
        
        try:
            status = router.poll_status(task_id, provider_name)
            poll_count += 1
            
            print(f"  [{elapsed}s] Poll #{poll_count}: {status}")
            
            if status == "SUCCEEDED":
                print("✅ Video generation succeeded!")
                return True
            elif status == "FAILED":
                print("❌ Video generation failed")
                return False
            
            # Wait before polling again
            time.sleep(10)
            
        except Exception as e:
            print(f"  [{elapsed}s] Poll error: {e}")
            time.sleep(5)
    
    print("⏱️  Timeout waiting for video")
    return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Decart Provider Test Suite")
    print("=" * 60)
    
    results = {}
    
    # Test 1: Provider router
    try:
        router = test_provider_router()
        results["router"] = True
    except Exception as e:
        print(f"❌ Router test failed: {e}")
        results["router"] = False
        return 1
    
    # Test 2: Decart provider submit
    test_result = test_decart_provider(router)
    results["decart_submit"] = test_result is not None
    
    if test_result:
        task_id, provider = test_result
        
        # Test 3: Poll for completion
        success = poll_for_completion(router, task_id, provider.name)
        results["decart_poll"] = success
        
        if success:
            # Test 4: Fetch output
            print("\n" + "=" * 60)
            print("Fetching Video Output")
            print("=" * 60)
            
            from genblaze_core.models.step import Step
            from genblaze_core import Modality
            
            step = Step(provider="decart", model="lucy-latest", prompt="", modality=Modality.VIDEO)
            
            try:
                step = provider.fetch_output(task_id, step)
                if step.assets:
                    video_url = step.assets[0].url
                    print(f"✅ Video fetched!")
                    print(f"   URL: {video_url[:100]}...")
                    results["decart_fetch"] = True
                else:
                    print("❌ No assets in result")
                    results["decart_fetch"] = False
            except Exception as e:
                print(f"❌ Fetch failed: {e}")
                results["decart_fetch"] = False
    else:
        results["decart_poll"] = False
        results["decart_fetch"] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    for name, result in results.items():
        status = "✅" if result else "❌"
        print(f"  {status} {name}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All tests passed!")
    else:
        print("⚠️  Some tests failed")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
