import { pipelineApi, pipelineEndpoints } from './pipelineApi';

export const sceneService = {
  create: (payload) => pipelineApi.post(pipelineEndpoints.scenes.create, payload),
  get: (sceneId) => pipelineApi.get(pipelineEndpoints.scenes.get(sceneId)),
  update: (sceneId, payload) => pipelineApi.put(pipelineEndpoints.scenes.update(sceneId), payload),
  delete: (sceneId) => pipelineApi.delete(pipelineEndpoints.scenes.delete(sceneId)),
  approve: (sceneId) => pipelineApi.put(pipelineEndpoints.scenes.approve(sceneId)),
  reject: (sceneId) => pipelineApi.put(pipelineEndpoints.scenes.reject(sceneId)),
  lock: (sceneId) => pipelineApi.put(pipelineEndpoints.scenes.lock(sceneId)),
  unlock: (sceneId) => pipelineApi.put(pipelineEndpoints.scenes.unlock(sceneId)),
  characters: (sceneId, payload) => pipelineApi.put(pipelineEndpoints.scenes.characters(sceneId), payload),
  reorder: (sceneId, payload) => pipelineApi.post(pipelineEndpoints.scenes.reorder(sceneId), payload),
  references: (sceneId, payload) => pipelineApi.put(pipelineEndpoints.scenes.references(sceneId), payload),
  regenerate: (sceneId) => pipelineApi.post(pipelineEndpoints.scenes.regenerate(sceneId)),
  history: (sceneId) => pipelineApi.get(pipelineEndpoints.scenes.history(sceneId)),
  jobStatus: (sceneId) => pipelineApi.get(pipelineEndpoints.scenes.jobStatus(sceneId)),
};
