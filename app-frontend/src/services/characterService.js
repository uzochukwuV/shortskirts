import { pipelineApi, pipelineEndpoints } from './pipelineApi';

export const characterService = {
  create: (payload) => pipelineApi.post(pipelineEndpoints.characters.create, payload),
  listByStory: (storyId) => pipelineApi.get(pipelineEndpoints.characters.byStory(storyId)),
  get: (characterId) => pipelineApi.get(pipelineEndpoints.characters.get(characterId)),
  update: (characterId, payload) => pipelineApi.put(pipelineEndpoints.characters.update(characterId), payload),
  delete: (characterId) => pipelineApi.delete(pipelineEndpoints.characters.delete(characterId)),
  approve: (characterId) => pipelineApi.put(pipelineEndpoints.characters.approve(characterId)),
  regenerateRefs: (characterId) => pipelineApi.post(pipelineEndpoints.characters.regenerateRefs(characterId)),
};
