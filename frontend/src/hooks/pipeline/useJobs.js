import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { jobService } from '@/services/jobService';

export const jobKeys = {
  all: ['jobs'],
  detail: (jobId) => [...jobKeys.all, 'detail', jobId],
  entity: (entityType, entityId) => [...jobKeys.all, 'entity', entityType, entityId],
  metrics: (jobId) => [...jobKeys.detail(jobId), 'metrics'],
};

export function useJob(jobId) {
  return useQuery({
    queryKey: jobKeys.detail(jobId),
    queryFn: () => jobService.get(jobId),
    enabled: Boolean(jobId),
    refetchInterval: 5000,
  });
}

export function useEntityJobs(entityType, entityId) {
  return useQuery({
    queryKey: jobKeys.entity(entityType, entityId),
    queryFn: () => jobService.byEntity(entityType, entityId),
    enabled: Boolean(entityType && entityId),
    refetchInterval: 5000,
  });
}

export function useJobMetrics(jobId) {
  return useQuery({
    queryKey: jobKeys.metrics(jobId),
    queryFn: () => jobService.metrics(jobId),
    enabled: Boolean(jobId),
  });
}

export function useCancelJob(jobId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => jobService.cancel(jobId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: jobKeys.detail(jobId) }),
  });
}

export function useRetryJob(jobId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => jobService.retry(jobId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: jobKeys.detail(jobId) }),
  });
}
