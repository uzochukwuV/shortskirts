import { pipelineApi, pipelineEndpoints } from './pipelineApi';

export const galleryService = {
  list: () => pipelineApi.get(pipelineEndpoints.gallery.list),
  public: () => pipelineApi.get(pipelineEndpoints.gallery.public),
};

export const providerService = {
  status: () => pipelineApi.get(pipelineEndpoints.providers.status),
};
