import { pipelineApi, pipelineEndpoints } from './pipelineApi';

export const storyService = {
  list: (query) => pipelineApi.get(pipelineEndpoints.stories.list, { query }),
  create: (payload) => pipelineApi.post(pipelineEndpoints.stories.create, payload),
  get: (storyId) => pipelineApi.get(pipelineEndpoints.stories.get(storyId)),
  update: (storyId, payload) => pipelineApi.put(pipelineEndpoints.stories.update(storyId), payload),
  assistant: (storyId, payload) => pipelineApi.post(pipelineEndpoints.stories.assistant(storyId), payload),
  regenerateOutline: (storyId) => pipelineApi.post(pipelineEndpoints.stories.regenerateOutline(storyId)),
  updatePipelineConfig: (storyId, payload) => pipelineApi.put(pipelineEndpoints.stories.pipelineConfig(storyId), payload),
  approveOutline: (storyId) => pipelineApi.put(pipelineEndpoints.stories.approveOutline(storyId)),
  launchGeneration: (storyId) => pipelineApi.post(pipelineEndpoints.stories.generate(storyId)),
  history: (storyId) => pipelineApi.get(pipelineEndpoints.stories.history(storyId)),
  batchDashboard: () => pipelineApi.get(pipelineEndpoints.stories.batchDashboard),
};
