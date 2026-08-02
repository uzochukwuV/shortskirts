import { useMutation, useQuery } from '@tanstack/react-query';
import { agentService } from '@/services/agentService';

export const agentKeys = {
  all: ['agent'],
  conversations: () => [...agentKeys.all, 'conversations'],
  conversation: (conversationId) => [...agentKeys.all, 'conversation', conversationId],
  tools: () => [...agentKeys.all, 'tools'],
  tool: (toolName) => [...agentKeys.all, 'tool', toolName],
  storyContext: (storyId) => [...agentKeys.all, 'story-context', storyId],
  storyTimeline: (storyId, sceneId) => [...agentKeys.all, 'story-timeline', storyId, sceneId],
  storyAssets: (storyId, query) => [...agentKeys.all, 'story-assets', storyId, query ?? {}],
  providerStatus: () => [...agentKeys.all, 'provider-status'],
};

export function useAgentTools() {
  return useQuery({
    queryKey: agentKeys.tools(),
    queryFn: agentService.tools,
  });
}

export function useAgentTool(toolName) {
  return useQuery({
    queryKey: agentKeys.tool(toolName),
    queryFn: () => agentService.tool(toolName),
    enabled: Boolean(toolName),
  });
}

export function useAgentConversations() {
  return useQuery({
    queryKey: agentKeys.conversations(),
    queryFn: agentService.conversations,
  });
}

export function useAgentConversation(conversationId) {
  return useQuery({
    queryKey: agentKeys.conversation(conversationId),
    queryFn: () => agentService.conversation(conversationId),
    enabled: Boolean(conversationId),
  });
}

export function useStoryContext(storyId) {
  return useQuery({
    queryKey: agentKeys.storyContext(storyId),
    queryFn: () => agentService.storyContext(storyId),
    enabled: Boolean(storyId),
  });
}

export function useStoryTimeline(storyId, sceneId) {
  return useQuery({
    queryKey: agentKeys.storyTimeline(storyId, sceneId),
    queryFn: () => agentService.storyTimeline(storyId, sceneId),
    enabled: Boolean(storyId && sceneId),
  });
}

export function useStoryAssets(storyId, query) {
  return useQuery({
    queryKey: agentKeys.storyAssets(storyId, query),
    queryFn: () => agentService.storyAssets(storyId, query),
    enabled: Boolean(storyId),
  });
}

export function useSearchStoryAssets(storyId) {
  return useMutation({
    mutationFn: (query) => agentService.searchStoryAssets(storyId, query),
  });
}

export function useProviderStatus() {
  return useQuery({
    queryKey: agentKeys.providerStatus(),
    queryFn: agentService.providerStatus,
    refetchInterval: 15000,
  });
}

export function useSendAgentChat() {
  return useMutation({
    mutationFn: agentService.chat,
  });
}

export function useExecuteTool() {
  return useMutation({
    mutationFn: agentService.executeTool,
  });
}
