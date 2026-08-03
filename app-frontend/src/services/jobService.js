import { pipelineApi, pipelineEndpoints } from './pipelineApi';

export const jobService = {
  get: (jobId) => pipelineApi.get(pipelineEndpoints.jobs.get(jobId)),
  byEntity: (entityType, entityId) => pipelineApi.get(pipelineEndpoints.jobs.byEntity(entityType, entityId)),
  metrics: (jobId) => pipelineApi.get(pipelineEndpoints.jobs.metrics(jobId)),
  cancel: (jobId) => pipelineApi.post(pipelineEndpoints.jobs.cancel(jobId)),
  retry: (jobId) => pipelineApi.post(pipelineEndpoints.jobs.retry(jobId)),
};
