#!/usr/bin/env python3
"""
Test script for Veo 3 provider via the provider router.

Usage: python test_veo3_provider.py
"""

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
    
    from pipeline.providers import get_router, ProviderType
    
    # Reset global router
    import pipeline.providers.provider_router as pr
    pr._router = None
    
    router = get_router()
    
    # Get status
    status = router.get_status_summary()
    print(f"\nProvider Status:")
    for name, info in status["providers"].items():
        enabled = "✅" if info["enabled"] else "❌"
        has_key = "🔑" if info["has_api_key"] else "🔒"
        priority = info["priority"]
        print(f"  {enabled} {has_key} {name:<12} (priority: {priority})")
    
    print(f"\nAvailable providers (by priority): {[p.value for p in router.available_providers]}")
    
    return router


def test_veo3_submit(router):
    """Test Veo 3 video submission."""
    print("\n" + "=" * 60)
    print("Testing Veo 3 Video Submission")
    print("=" * 60)
    
    from genblaze_core.models.step import Step
    from genblaze_core import Modality
    from pipeline.providers import ProviderType
    
    # Check if Veo 3 is available
    if ProviderType.VEO3 not in router.available_providers:
        print("❌ Veo 3 not available")
        return None
    
    # Get Veo 3 provider
    provider = router.get_provider(ProviderType.VEO3)
    print(f"✅ Using provider: {provider.name}")
    
    # Check API key
    api_key = os.environ.get("VEO3_API_KEY", "")
    if api_key:
        masked = f"{api_key[:8]}...{api_key[-4:]}"
        print(f"🔑 API key: {masked}")
    
    # Create a test step
    step = Step(
        provider="veo3",
        model="veo3-fast",  # Use fast model for testing
        prompt="A beautiful anime girl with pink hair standing in a flower garden, cinematic lighting, high quality",
        modality=Modality.VIDEO,
    )
    step.params = {
        "aspect_ratio": "16:9",
    }
    
    print(f"\n📤 Submitting video generation...")
    print(f"   Model: {step.model}")
    print(f"   Prompt: {step.prompt[:60]}...")
    print(f"   Aspect Ratio: {step.params.get('aspect_ratio')}")
    
    try:
        task_id = provider.submit(step)
        print(f"✅ Task submitted: {task_id}")
        return task_id, provider
    except Exception as e:
        error_msg = str(e)
        if "402" in error_msg or "No credit" in error_msg:
            print(f"⚠️  API key valid but no credits remaining")
            print(f"   Please add credits at https://veo3api.com/pricing")
        else:
            print(f"❌ Submit failed: {e}")
            import traceback
            traceback.print_exc()
        return None


def poll_for_completion(router, task_id, provider_name, max_wait=600):
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
            
            if status == "COMPLETED":
                print("✅ Video generation completed!")
                return True
            elif status == "FAILED":
                print("❌ Video generation failed")
                return False
            
            # Wait before polling again (Veo 3 typically takes 30-90s)
            time.sleep(15)
            
        except Exception as e:
            print(f"  [{elapsed}s] Poll error: {e}")
            time.sleep(10)
    
    print("⏱️  Timeout waiting for video")
    return False


def test_fetch_output(router, task_id, provider):
    """Test fetching the video output."""
    print("\n" + "=" * 60)
    print("Fetching Video Output")
    print("=" * 60)
    
    from genblaze_core.models.step import Step
    from genblaze_core import Modality
    
    step = Step(provider="veo3", model="veo3-fast", prompt="", modality=Modality.VIDEO)
    
    try:
        step = provider.fetch_output(task_id, step)
        if step.assets:
            video_url = step.assets[0].url
            print(f"✅ Video fetched!")
            print(f"   URL: {video_url[:100]}...")
            return video_url
        else:
            print("❌ No assets in result")
            return None
    except Exception as e:
        print(f"❌ Fetch failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run all tests."""
    print("=" * 60)
    print("Veo 3 Provider Test Suite")
    print("=" * 60)
    
    results = {}
    video_url = None
    
    # Test 1: Provider router
    try:
        router = test_provider_router()
        results["router"] = True
    except Exception as e:
        print(f"❌ Router test failed: {e}")
        results["router"] = False
        return 1
    
    # Test 2: Veo 3 submit
    test_result = test_veo3_submit(router)
    results["veo3_submit"] = test_result is not None
    
    if test_result:
        task_id, provider = test_result
        
        # Test 3: Poll for completion
        success = poll_for_completion(router, task_id, provider.name)
        results["veo3_poll"] = success
        
        if success:
            # Test 4: Fetch output
            video_url = test_fetch_output(router, task_id, provider)
            results["veo3_fetch"] = video_url is not None
        else:
            results["veo3_fetch"] = False
    else:
        results["veo3_poll"] = False
        results["veo3_fetch"] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    for name, result in results.items():
        status = "✅" if result else "❌"
        print(f"  {status} {name}")
    
    if video_url:
        print(f"\n🎬 Generated Video URL:")
        print(f"   {video_url}")
    
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
