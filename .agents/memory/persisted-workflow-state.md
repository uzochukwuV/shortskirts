---
name: Persisted workflow state
description: Provider-selection constraints for stories imported or created before the current pipeline defaults.
---

Persisted story workflow state can contain provider preferences and durations from an older pipeline version. Provider selection must normalize that state before planning or rendering; disabling a provider only in current defaults is not sufficient.

**Why:** An existing approved story retained an older AIML preference and legacy model-registry planner, which bypassed the newer GenBlaze-only route.

**How to apply:** Keep provider planning tied to the live adapter router, filter disabled providers during normalization, and cap imported duration settings before any generation attempt.

HappyHorse/DashScope rejects requests shorter than 3 seconds, so the effective credit-safe duration is 3 seconds rather than 2.

**Why:** A direct 2-second HappyHorse submission was accepted as a task but failed at provider polling with a minimum-duration error.

**How to apply:** Enforce the 3-second minimum before building the GenBlaze `Step`, including direct tests and imported story settings.