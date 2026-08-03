---
name: Qwen video fallback
description: The active reference-video model order for the Qwen/DashScope route.
---

For reference-to-video generation through the Qwen/DashScope route, try `happyhorse-1.1-r2v` first and then `wan2.7-r2v-2026-06-12`. This fallback is a model-level fallback inside the Qwen route; it does not replace or remove the other configured provider fallbacks.

**Why:** The active workflow is currently using Qwen/DashScope, while the dated Wan model is the required fallback when HappyHorse account access fails.

**How to apply:** Keep this model order in scene-generation attempts and preserve the existing provider preference list unless the user explicitly changes provider routing.