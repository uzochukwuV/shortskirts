import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { storyService } from '@/services/storyService';

export const storyKeys = {
  all: ['stories'],
  lists: () => [...storyKeys.all, 'list'],
  list: (query) => [...storyKeys.lists(), query ?? {}],
  detail: (storyId) => [...storyKeys.all, 'detail', storyId],
  history: (storyId) => [...storyKeys.detail(storyId), 'history'],
  batchDashboard: () => [...storyKeys.all, 'batch-dashboard'],
};

export function useStories(query) {
  return useQuery({
    queryKey: storyKeys.list(query),
    queryFn: () => storyService.list(query),
  });
}

export function useStory(storyId) {
  return useQuery({
    queryKey: storyKeys.detail(storyId),
    queryFn: () => storyService.get(storyId),
    enabled: Boolean(storyId),
  });
}

export function useStoryHistory(storyId) {
  return useQuery({
    queryKey: storyKeys.history(storyId),
    queryFn: () => storyService.history(storyId),
    enabled: Boolean(storyId),
  });
}

export function useBatchDashboard() {
  return useQuery({
    queryKey: storyKeys.batchDashboard(),
    queryFn: storyService.batchDashboard,
  });
}

export function useCreateStory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: storyService.create,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: storyKeys.all }),
  });
}

export function useUpdateStory(storyId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload) => storyService.update(storyId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: storyKeys.detail(storyId) }),
  });
}

export function useRegenerateOutline(storyId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => storyService.regenerateOutline(storyId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: storyKeys.detail(storyId) }),
  });
}

export function useUpdatePipelineConfig(storyId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload) => storyService.updatePipelineConfig(storyId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: storyKeys.detail(storyId) }),
  });
}

export function useApproveStoryOutline(storyId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => storyService.approveOutline(storyId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: storyKeys.detail(storyId) }),
  });
}

export function useLaunchStoryGeneration(storyId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => storyService.launchGeneration(storyId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: storyKeys.detail(storyId) }),
  });
}

export function useStoryAssistant(storyId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload) => storyService.assistant(storyId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: storyKeys.detail(storyId) }),
  });
}
