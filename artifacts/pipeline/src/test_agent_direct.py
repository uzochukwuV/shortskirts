#!/usr/bin/env python3
"""
Direct test of the agent system without the full server.
This bypasses init_db and tests the core functionality.
"""

import asyncio
import os
import sys
import ssl
import json
import asyncpg
from datetime import datetime

# Setup path
sys.path.insert(0, os.path.dirname(__file__))

# Load env
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from pipeline.agent_llm import ChatMessage, agent_chat
from pipeline.agent_tools import get_all_tools, get_story_context_impl
from pipeline.agent_service import execute_tool

# Global pool for testing
_pool = None

async def get_test_pool():
    global _pool
    if _pool is None:
        url = os.environ.get("COCKROACHDB_URL")
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        
        _pool = await asyncpg.create_pool(
            url,
            ssl=ssl_ctx,
            min_size=1,
            max_size=3,
            command_timeout=60,
        )
    return _pool


async def find_or_create_test_story(pool):
    """Find an existing story or create a test one."""
    # Try to find an existing story
    story = await pool.fetchrow(
        "SELECT * FROM stories WHERE status = 'draft' LIMIT 1"
    )
    
    if story:
        print(f"Using existing story: {story['id']} - {story['title']}")
        return dict(story)
    
    # Create a test story
    print("Creating test story...")
    story = await pool.fetchrow(
        """INSERT INTO stories (title, prompt, status, workflow_type, owner_id)
           VALUES ('Test Story: The Coffee Shop', 'A story about a curious barista', 'draft', 'creator_series', gen_random_uuid())
           RETURNING *""",
    )
    print(f"Created story: {story['id']}")
    return dict(story)


async def find_or_create_test_episode(pool, story_id):
    """Find an existing episode or create one."""
    episode = await pool.fetchrow(
        "SELECT * FROM episodes WHERE story_id = $1 LIMIT 1",
        story_id
    )
    
    if episode:
        print(f"Using existing episode: {episode['id']}")
        return dict(episode)
    
    print("Creating test episode...")
    episode = await pool.fetchrow(
        """INSERT INTO episodes (story_id, episode_number, title, status)
           VALUES ($1, 1, 'Episode 1: The Beginning', 'draft')
           RETURNING *""",
        story_id
    )
    print(f"Created episode: {episode['id']}")
    return dict(episode)


async def test_get_story_context(pool, story):
    """Test: Get story context."""
    print("\n" + "="*60)
    print("TEST: Get Story Context")
    print("="*60)
    
    try:
        context = await get_story_context_impl(pool, story["id"])
        print(f"✅ Story: {context['title']}")
        print(f"   Episodes: {len(context['episodes'])}")
        print(f"   Scenes: {sum(len(ep['scenes']) for ep in context['episodes'])}")
        print(f"   Characters: {len(context['characters'])}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_create_scene(pool, story, episode):
    """Test: Create a new scene."""
    print("\n" + "="*60)
    print("TEST: Create Scene")
    print("="*60)
    
    try:
        # Simulate the agent calling create_scene
        scene_data = {
            "title": "Mara Enters the Coffee Shop",
            "description": "Mara, a curious young barista, pushes open the door of a cozy coffee shop on a rainy morning. She shakes the water from her umbrella and takes in the warm, aromatic atmosphere.",
            "location": "Cozy coffee shop",
            "mood": "warm, inviting, cozy",
            "action": "Mara enters, shakes umbrella, looks around",
            "duration_seconds": 5,
        }
        
        result = await execute_tool(
            "create_scene",
            {
                "story_id": story["id"],
                "episode_id": episode["id"],
                "scene_data": scene_data,
            },
            pool
        )
        
        if result.get("success"):
            r = result["result"]
            print(f"✅ Scene created: {r.get('title')}")
            print(f"   Scene ID: {r.get('id')}")
            print(f"   Scene Number: {r.get('scene_number')}")
            print(f"   Job ID: {r.get('job_id')}")
            print(f"   Poll URL: {r.get('poll_url')}")
            return r
        else:
            print(f"❌ Error: {result.get('error')}")
            return None
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_delete_scene(pool, story_id, scene_id):
    """Test: Delete a scene."""
    print("\n" + "="*60)
    print("TEST: Delete Scene")
    print("="*60)
    
    try:
        result = await execute_tool(
            "delete_scene",
            {
                "story_id": story_id,
                "scene_id": scene_id,
            },
            pool
        )
        
        if result.get("success"):
            print(f"✅ Scene deleted: {scene_id}")
            return True
        else:
            print(f"❌ Error: {result.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False


async def test_llm_with_tools(pool, story):
    """Test: LLM with tool calling."""
    print("\n" + "="*60)
    print("TEST: LLM with Tool Calling")
    print("="*60)
    
    # Get story context
    context = await get_story_context_impl(pool, story["id"])
    
    system_prompt = f"""You are an AI assistant for a video production platform.
Current story: {context['title']}
Episodes: {len(context['episodes'])}
Scenes in episode 1: {len(context['episodes'][0]['scenes']) if context['episodes'] else 0}

You can use tools to:
- get_story_context: Get full story info
- create_scene: Create a new scene
- update_scene: Modify a scene
- delete_scene: Remove a scene
- generate_scene_description: Generate scene details with AI

Be helpful and creative in your responses."""

    messages = [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content="List the current scenes in my story and tell me what we have so far."),
    ]
    
    tools = get_all_tools()
    print(f"Using {len(tools)} tools...")
    
    try:
        response = await agent_chat(
            messages=messages,
            tools=tools,
            temperature=0.7,
            max_tokens=1000,
        )
        
        print(f"\n📝 LLM Response:")
        print("-" * 40)
        print(response.content)
        print("-" * 40)
        
        print(f"\n🔧 Tool Calls: {len(response.tool_calls)}")
        for tc in response.tool_calls:
            print(f"   - {tc.name}: {tc.arguments}")
        
        return True
    except Exception as e:
        print(f"❌ LLM Error: {e}")
        return False


async def test_job_polling(pool):
    """Test: Job polling capability."""
    print("\n" + "="*60)
    print("TEST: Job Polling")
    print("="*60)
    
    try:
        # Get recent jobs
        jobs = await pool.fetch(
            """SELECT * FROM generation_jobs 
               ORDER BY created_at DESC LIMIT 5"""
        )
        
        if jobs:
            print(f"Found {len(jobs)} recent jobs:")
            for job in jobs:
                print(f"  - Job {job['id']}: {job['status']} ({job['job_type']})")
            return True
        else:
            print("No jobs found (expected - none created yet)")
            return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_reference_images(pool, story):
    """Test: Reference image handling."""
    print("\n" + "="*60)
    print("TEST: Reference Images")
    print("="*60)
    
    # Check if there's a way to add reference images
    try:
        # Get scenes to check if they have reference images
        scenes = await pool.fetch(
            """SELECT s.*, sc.reference_image_urls
               FROM scenes s
               JOIN episodes e ON s.episode_id = e.id
               WHERE e.story_id = $1
               LIMIT 5""",
            story["id"]
        )
        
        print(f"Found {len(scenes)} scenes")
        for scene in scenes:
            refs = scene.get("reference_image_urls") or []
            print(f"  Scene {scene['scene_number']}: {len(refs)} reference images")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_screenshot_continuity(pool, story):
    """Test: Screenshot continuity - can we extract frames from previous scenes?"""
    print("\n" + "="*60)
    print("TEST: Screenshot/Continuity Feature")
    print("="*60)
    
    try:
        # Check if there are any scenes with video URLs
        scenes = await pool.fetch(
            """SELECT s.id, s.scene_number, s.clip_url, s.image_url, s.exit_frame_url
               FROM scenes s
               JOIN episodes e ON s.episode_id = e.id
               WHERE e.story_id = $1
                 AND (s.clip_url IS NOT NULL OR s.image_url IS NOT NULL)
               LIMIT 5""",
            story["id"]
        )
        
        if scenes:
            print(f"Found {len(scenes)} scenes with media:")
            for scene in scenes:
                print(f"  Scene {scene['scene_number']}:")
                print(f"    - clip_url: {scene['clip_url'][:50] if scene['clip_url'] else 'None'}...")
                print(f"    - image_url: {scene['image_url'][:50] if scene['image_url'] else 'None'}...")
                print(f"    - exit_frame_url: {scene['exit_frame_url'][:50] if scene['exit_frame_url'] else 'None'}...")
        else:
            print("No scenes with media found yet")
        
        # Check if there's a tool for continuity
        print("\nChecking available tools for continuity...")
        tools = get_all_tools()
        continuity_tools = [t for t in tools if "continuity" in t.get("function", {}).get("description", "").lower() 
                          or "exit_frame" in t.get("function", {}).get("description", "").lower()]
        if continuity_tools:
            print(f"Found continuity tools: {[t['function']['name'] for t in continuity_tools]}")
        else:
            print("No explicit continuity tools found")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("="*60)
    print("AGENT SYSTEM TEST")
    print("="*60)
    
    pool = await get_test_pool()
    print("✅ Database pool created")
    
    # Setup test data
    story = await find_or_create_test_story(pool)
    episode = await find_or_create_test_episode(pool, story["id"])
    
    results = {}
    
    # Run tests
    results["get_story_context"] = await test_get_story_context(pool, story)
    results["create_scene"] = await test_create_scene(pool, story, episode)
    results["llm_with_tools"] = await test_llm_with_tools(pool, story)
    results["job_polling"] = await test_job_polling(pool)
    results["reference_images"] = await test_reference_images(pool, story)
    results["screenshot_continuity"] = await test_screenshot_continuity(pool, story)
    
    # Cleanup - delete test scene if created
    if results.get("create_scene"):
        scene_id = results["create_scene"].get("id")
        if scene_id:
            await test_delete_scene(pool, story["id"], scene_id)
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    # Cleanup
    await pool.close()
    print("\n✅ All tests completed")


if __name__ == "__main__":
    asyncio.run(main())
