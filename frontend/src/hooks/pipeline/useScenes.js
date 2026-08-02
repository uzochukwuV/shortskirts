import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { sceneService } from '@/services/sceneService';

export const sceneKeys = {
  all: ['scenes'],
  detail: (sceneId) => [...sceneKeys.all, 'detail', sceneId],
  history: (sceneId) => [...sceneKeys.detail(sceneId), 'history'],
  jobStatus: (sceneId) => [...sceneKeys.detail(sceneId), 'job-status'],
};

export function useScene(sceneId) {
  return useQuery({
    queryKey: sceneKeys.detail(sceneId),
    queryFn: () => sceneService.get(sceneId),
    enabled: Boolean(sceneId),
  });
}

export function useSceneHistory(sceneId) {
  return useQuery({
    queryKey: sceneKeys.history(sceneId),
    queryFn: () => sceneService.history(sceneId),
    enabled: Boolean(sceneId),
  });
}

export function useSceneJobStatus(sceneId) {
  return useQuery({
    queryKey: sceneKeys.jobStatus(sceneId),
    queryFn: () => sceneService.jobStatus(sceneId),
    enabled: Boolean(sceneId),
    refetchInterval: 5000,
  });
}

export function useCreateScene() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: sceneService.create,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: sceneKeys.all }),
  });
}

export function useUpdateScene(sceneId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload) => sceneService.update(sceneId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: sceneKeys.detail(sceneId) }),
  });
}

export function useApproveScene(sceneId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => sceneService.approve(sceneId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: sceneKeys.detail(sceneId) }),
  });
}

export function useRegenerateScene(sceneId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => sceneService.regenerate(sceneId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: sceneKeys.detail(sceneId) }),
  });
}

export function useLockScene(sceneId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (locked = true) => locked ? sceneService.lock(sceneId) : sceneService.unlock(sceneId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: sceneKeys.detail(sceneId) }),
  });
}
