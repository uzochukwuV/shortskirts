import { pipelineApi, pipelineEndpoints } from './pipelineApi';

export const agentService = {
  conversations: () => pipelineApi.get(pipelineEndpoints.agent.conversations),
  conversation: (conversationId) => pipelineApi.get(pipelineEndpoints.agent.conversation(conversationId)),
  chat: (payload) => pipelineApi.post(pipelineEndpoints.agent.chat, payload),
  chatStream: (conversationId, query) => pipelineApi.get(pipelineEndpoints.agent.chatStream(conversationId), { query }),
  tools: () => pipelineApi.get(pipelineEndpoints.agent.tools),
  tool: (toolName) => pipelineApi.get(pipelineEndpoints.agent.tool(toolName)),
  executeTool: (payload) => pipelineApi.post(pipelineEndpoints.agent.executeTool, payload),
  storyContext: (storyId) => pipelineApi.get(pipelineEndpoints.agent.storyContext(storyId)),
  storyTimeline: (storyId, sceneId) => pipelineApi.get(pipelineEndpoints.agent.storyTimeline(storyId, sceneId)),
  storyAssets: (storyId, query) => pipelineApi.get(pipelineEndpoints.agent.storyAssets(storyId), { query }),
  searchStoryAssets: (storyId, query) => pipelineApi.get(pipelineEndpoints.agent.searchStoryAssets(storyId), { query }),
  providerStatus: () => pipelineApi.get(pipelineEndpoints.agent.providerStatus),
};
