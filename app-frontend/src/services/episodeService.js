import { pipelineApi, pipelineEndpoints } from './pipelineApi';

export const episodeService = {
  listByStory: (storyId) => pipelineApi.get(pipelineEndpoints.episodes.byStory(storyId)),
  get: (episodeId) => pipelineApi.get(pipelineEndpoints.episodes.get(episodeId)),
  assemble: (episodeId) => pipelineApi.post(pipelineEndpoints.episodes.assemble(episodeId)),
  bulkApprove: (episodeId) => pipelineApi.put(pipelineEndpoints.episodes.bulkApprove(episodeId)),
};
