import { sessionStorage } from './session';

const DEFAULT_API_BASE = import.meta.env.VITE_PIPELINE_API_BASE_URL || '/pipeline';

const readStorageToken = () => sessionStorage.getToken();

const toQueryString = (params = {}) => {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue;
    if (Array.isArray(value)) {
      value.forEach((item) => {
        if (item !== undefined && item !== null && item !== '') {
          search.append(key, String(item));
        }
      });
      continue;
    }
    search.set(key, String(value));
  }
  const query = search.toString();
  return query ? `?${query}` : '';
};

const buildUrl = (path, query) => `${DEFAULT_API_BASE}${path}${toQueryString(query)}`;

export class PipelineApiError extends Error {
  constructor(message, { status, data, url, method } = {}) {
    super(message);
    this.name = 'PipelineApiError';
    this.status = status;
    this.data = data;
    this.url = url;
    this.method = method;
  }
}

const parseResponse = async (response) => {
  const contentType = response.headers.get('content-type') || '';
  if (response.status === 204) return null;
  if (contentType.includes('application/json')) {
    return response.json();
  }
  return response.text();
};

export const request = async (path, { method = 'GET', query, body, headers = {}, token, signal } = {}) => {
  const url = buildUrl(path, query);
  const authToken = token ?? readStorageToken();
  const finalHeaders = { ...headers };

  if (!(body instanceof FormData) && body !== undefined) {
    finalHeaders['Content-Type'] = finalHeaders['Content-Type'] || 'application/json';
  }
  if (authToken) {
    finalHeaders.Authorization = `Bearer ${authToken}`;
  }

  const response = await fetch(url, {
    method,
    headers: finalHeaders,
    body: body instanceof FormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
    signal,
  });

  const data = await parseResponse(response).catch(() => null);
  if (!response.ok) {
    const message = (data && typeof data === 'object' && (data.detail || data.message || data.error))
      || response.statusText
      || 'Request failed';
    throw new PipelineApiError(message, {
      status: response.status,
      data,
      url,
      method,
    });
  }

  return data;
};

export const pipelineEndpoints = {
  auth: {
    register: '/auth/register',
    login: '/auth/login',
    me: '/auth/me',
    logout: '/auth/logout',
  },
  stories: {
    list: '/stories',
    create: '/stories',
    get: (storyId) => `/stories/${storyId}`,
    update: (storyId) => `/stories/${storyId}`,
    assistant: (storyId) => `/stories/${storyId}/assistant`,
    regenerateOutline: (storyId) => `/stories/${storyId}/regenerate-outline`,
    pipelineConfig: (storyId) => `/stories/${storyId}/pipeline-config`,
    approveOutline: (storyId) => `/stories/${storyId}/approve-outline`,
    generate: (storyId) => `/stories/${storyId}/generate`,
    history: (storyId) => `/stories/${storyId}/history`,
    batchDashboard: '/stories/batch/dashboard',
  },
  scenes: {
    create: '/scenes',
    get: (sceneId) => `/scenes/${sceneId}`,
    update: (sceneId) => `/scenes/${sceneId}`,
    delete: (sceneId) => `/scenes/${sceneId}`,
    approve: (sceneId) => `/scenes/${sceneId}/approve`,
    reject: (sceneId) => `/scenes/${sceneId}/reject`,
    lock: (sceneId) => `/scenes/${sceneId}/lock`,
    unlock: (sceneId) => `/scenes/${sceneId}/unlock`,
    characters: (sceneId) => `/scenes/${sceneId}/characters`,
    reorder: (sceneId) => `/scenes/${sceneId}/reorder`,
    references: (sceneId) => `/scenes/${sceneId}/references`,
    regenerate: (sceneId) => `/scenes/${sceneId}/regenerate`,
    history: (sceneId) => `/scenes/${sceneId}/history`,
    jobStatus: (sceneId) => `/scenes/${sceneId}/job-status`,
  },
  episodes: {
    byStory: (storyId) => `/episodes/story/${storyId}`,
    get: (episodeId) => `/episodes/${episodeId}`,
    bulkApprove: (episodeId) => `/episodes/${episodeId}/bulk-approve`,
    assemble: (episodeId) => `/episodes/${episodeId}/assemble`,
  },
  characters: {
    create: '/characters',
    byStory: (storyId) => `/characters/story/${storyId}`,
    get: (characterId) => `/characters/${characterId}`,
    update: (characterId) => `/characters/${characterId}`,
    delete: (characterId) => `/characters/${characterId}`,
    reject: (characterId) => `/characters/${characterId}/reject`,
    references: (characterId) => `/characters/${characterId}/references`,
    approve: (characterId) => `/characters/${characterId}/approve`,
    lock: (characterId) => `/characters/${characterId}/lock`,
    unlock: (characterId) => `/characters/${characterId}/unlock`,
    regenerateRefs: (characterId) => `/characters/${characterId}/regenerate-refs`,
  },
  bibles: {
    create: '/bibles',
    byStory: (storyId) => `/bibles/story/${storyId}`,
    get: (bibleId) => `/bibles/${bibleId}`,
    update: (bibleId) => `/bibles/${bibleId}`,
    delete: (bibleId) => `/bibles/${bibleId}`,
  },
  checkpoints: {
    byStory: (storyId) => `/stories/${storyId}/checkpoints`,
    approve: (storyId, checkpointId) => `/stories/${storyId}/checkpoints/${checkpointId}/approve`,
    history: (storyId, checkpointId) => `/stories/${storyId}/checkpoints/${checkpointId}/history`,
    audioRegenerate: (storyId, checkpointId) => `/stories/${storyId}/checkpoints/${checkpointId}/audio/regenerate`,
  },
  jobs: {
    get: (jobId) => `/jobs/${jobId}`,
    byEntity: (entityType, entityId) => `/jobs/entity/${entityType}/${entityId}`,
    metrics: (jobId) => `/jobs/${jobId}/metrics`,
    cancel: (jobId) => `/jobs/${jobId}/cancel`,
    retry: (jobId) => `/jobs/${jobId}/retry`,
  },
  chat: {
    create: '/chat',
    conversations: '/chat/conversations',
    conversation: (conversationId) => `/chat/${conversationId}`,
  },
  agent: {
    conversations: '/agent/conversations',
    conversation: (conversationId) => `/agent/conversations/${conversationId}`,
    chat: '/agent/chat',
    chatStream: (conversationId) => `/agent/chat-stream/${conversationId}`,
    tools: '/agent/tools',
    tool: (toolName) => `/agent/tools/${toolName}`,
    executeTool: '/agent/tools/execute',
    storyContext: (storyId) => `/agent/stories/${storyId}/context`,
    storyTimeline: (storyId, sceneId) => `/agent/stories/${storyId}/timeline/${sceneId}`,
    storyAssets: (storyId) => `/agent/stories/${storyId}/assets`,
    searchStoryAssets: (storyId) => `/agent/stories/${storyId}/assets/search`,
    providerStatus: '/agent/providers/status',
  },
  gallery: {
    list: '/gallery',
    public: '/gallery/public',
  },
  providers: {
    status: '/providers/status',
  },
};

export const pipelineApi = {
  get: (path, options = {}) => request(path, { ...options, method: 'GET' }),
  post: (path, body, options = {}) => request(path, { ...options, method: 'POST', body }),
  put: (path, body, options = {}) => request(path, { ...options, method: 'PUT', body }),
  delete: (path, options = {}) => request(path, { ...options, method: 'DELETE' }),
};

export default pipelineApi;
