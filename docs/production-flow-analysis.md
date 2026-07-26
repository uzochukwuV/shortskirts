# Video Production Flow Analysis - Dysentry

**Date:** 2026-07-26  
**Analyst:** OpenHands Agent

---

## Executive Summary

The Dysentry video production system implements a batch processing pipeline with Redis-based job queuing. Analysis reveals **5 critical bugs**, **7 medium bugs**, and **5 low bugs**, plus **6 major optimization opportunities**.

---

## Critical Bugs

### BUG-1: Race Condition - Duplicate Scene Regeneration (Severity: HIGH)
**File:** `artifacts/pipeline/src/routes/scenes.py:685-710`

**Problem:** Between SELECT and UPDATE, another concurrent request could pass the status check and enqueue a duplicate job.

```python
# CURRENT (BUGGY)
scene = await pool.fetchrow("SELECT * FROM scenes WHERE id=$1", scene_id)
if scene.get("status") == "running":
    raise HTTPException(status_code=409, detail="Scene generation already in progress")
# ... time gap ...
await pool.execute("UPDATE scenes SET status='running'...")
await enqueue_job(job_id, workload=WORKLOAD_MEDIA)
```

**Fix:** Use atomic conditional UPDATE with RETURNING clause.

---

### BUG-7: Sequential Scene Generation (Severity: HIGH - 20x Slower)
**File:** `artifacts/pipeline/src/orchestrator.py:~400-550`

**Problem:** Scenes are generated ONE AT A TIME even when within the same episode with no dependencies.

**Fix:** Use `asyncio.gather()` for parallel generation within episodes.

---

## High Priority Bugs

### BUG-6: Race Condition - Duplicate Story Generation
**File:** `artifacts/pipeline/src/routes/stories.py:~580-620`

### BUG-3: Job Loss Between Redis and PostgreSQL
**File:** `artifacts/pipeline/src/worker.py:183-195`

### BUG-13: Orphaned B2 Assets on DB Failure
**File:** `artifacts/pipeline/src/pipeline/job_handlers.py:~550-620`

---

## Medium Priority Bugs

### BUG-2: KeyError on Missing Env Var
**File:** `artifacts/pipeline/src/pipeline/audio_gen.py:67`

### BUG-8: Sequential Provider Status Probes
**File:** `artifacts/pipeline/src/pipeline/provider_status.py:193-210`

### BUG-9: Sequential Clip Downloads
**File:** `artifacts/pipeline/src/pipeline/assembler.py:22-35`

### BUG-15: N+1 Query Problem
**File:** `web/src/pages/Dashboard.jsx:30-45`

### BUG-16: No Job Completion Polling
**File:** `web/src/pages/Editor.jsx`

### BUG-17: Missing Unlock Endpoint
**File:** `artifacts/pipeline/src/routes/scenes.py`

---

## Low Priority Bugs

### BUG-4: Non-Atomic Metrics Recording
### BUG-5: Status Ambiguity
### BUG-11: Silent Exit Frame Failure
### BUG-12: Lost Intermediate Failures
### BUG-14: Fake Dashboard Chart Data

---

## Optimization Opportunities

| Opportunity | Impact |
|-------------|--------|
| Parallel Scene Generation | 20x faster |
| Batch API Endpoint | N+1 fix |
| Parallel Clip Downloads | 10x faster |
| Parallel Provider Probes | 3x faster |
| Incremental Episode Assembly | Faster resumes |
| Scene Generation Cache | Skip repeated work |

---

## Recommended Fix Order

1. **BUG-7** (Parallel scene gen) - Biggest performance win
2. **BUG-1, BUG-6** (Race conditions) - Prevent data corruption
3. **BUG-15** (N+1 queries) - Major frontend performance
4. **BUG-16** (Job polling) - UX fix
5. **BUG-14** (Fake data) - Misleading UI
6. **BUG-8, BUG-9** (Parallel operations) - Quick wins
7. **BUG-2, BUG-13** (Error handling) - Reliability

---

## Files Reference

### Backend (artifacts/pipeline/src/)
- `orchestrator.py` - Main story generation orchestrator
- `worker.py` - Async job worker with heartbeat/retries
- `pipeline/generation_coordinator.py` - Provider routing
- `pipeline/scene_gen.py` - Video clip generation
- `pipeline/assembler.py` - FFmpeg episode assembly
- `routes/scenes.py` - Scene CRUD + endpoints
- `routes/stories.py` - Story CRUD + generation

### Frontend (web/src/)
- `pages/Dashboard.jsx` - Production status dashboard
- `pages/Editor.jsx` - Scene editing + regeneration
- `api/dysentryClient.js` - Production API client
