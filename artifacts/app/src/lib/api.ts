export type WorkflowType =
  | "creator_series"
  | "brand_campaign"
  | "social_short"
  | "educational"
  | "game_lore"
  | "narrated_image_story";

export type BibleType = "brand" | "character" | "world" | "campaign";

export type Story = {
  id: string;
  title: string;
  prompt: string;
  genre: string;
  style: string;
  num_episodes?: number;
  num_scenes?: number;
  status: "draft" | "approved" | "generating" | "checkpoint_review" | "completed" | "ready" | "failed";
  approval_status: "pending_approval" | "approved";
  workflow_type: WorkflowType;
  workflow_version?: string;
  generation_version?: string;
  workflow_state?: Record<string, any> | null;
  episode_plan?: {
    synopsis: string;
    setting: string;
    themes: string[];
    characters: any[];
    episodes: any[];
  };
  created_at: string;
  updated_at: string;
};

export type Bible = {
  id: string;
  story_id?: string;
  bible_type: BibleType;
  name: string;
  content: Record<string, any>;
  created_at: string;
  updated_at: string;
};

export type Character = {
  id: string;
  story_id: string;
  name: string;
  role: string;
  description: string;
  personality: string;
  appearance: string;
  ref_image_urls: string[];
  approval_status: "pending" | "approved" | "rejected" | "locked";
  locked: boolean;
  created_at: string;
};

export type Episode = {
  id: string;
  story_id: string;
  episode_number: number;
  title: string;
  summary?: string;
  status: string;
  assembled_video_url?: string;
  scenes: Scene[];
};

export type Scene = {
  id: string;
  episode_id: string;
  scene_number: number;
  prompt: string;
  clip_url?: string;
  image_url?: string;
  media_url?: string;
  video_url?: string;
  exit_frame_url?: string;
  duration?: number;
  status: string;
  approval_status: "pending" | "approved" | "rejected" | "locked";
  locked: boolean;
  regeneration_count: number;
  generation_version?: string;
  image_model?: string | null;
  image_model_version?: string | null;
  edit_model?: string | null;
  edit_model_version?: string | null;
  source_scene_id?: string | null;
  state_snapshot?: Record<string, any> | null;
  title?: string;
  description?: string;
  visual_prompt?: string;
  mood?: string;
  location?: string;
  narration?: string;
  media_kind?: "image" | "video";
};

export type User = {
  id: string;
  email: string;
  created_at: string;
};

export type AuthResponse = {
  token: string;
  user: User;
};

export type AdminProfile = {
  email: string;
  role: "admin";
};

export type AdminAuthResponse = {
  token: string;
  admin: AdminProfile;
};

export type AdminUserSummary = {
  id: string;
  email: string;
  created_at: string;
  updated_at: string;
  story_count: number;
  draft_story_count: number;
  approved_story_count: number;
  generating_story_count: number;
  checkpoint_story_count: number;
  completed_story_count: number;
  failed_story_count: number;
  total_job_count: number;
  completed_job_count: number;
  failed_job_count: number;
  last_activity_at?: string | null;
  last_story_title?: string | null;
  last_story_status?: string | null;
};

export type AdminStorySummary = {
  id: string;
  title: string;
  status: string;
  approval_status: string;
  workflow_type: string;
  workflow_version?: string | null;
  generation_version?: string | null;
  episode_count: number;
  completed_episode_count: number;
  failed_episode_count: number;
  job_count: number;
  failed_job_count: number;
  created_at: string;
  updated_at: string;
};

export type AdminOverview = {
  totals: Record<string, number>;
  story_status_breakdown: { status: string; count: number }[];
  job_status_breakdown: { status: string; count: number }[];
  daily_activity: { day: string; count: number }[];
  provider_costs: { total_cost: number; avg_latency_ms: number; p95_latency_ms: number };
  provider_latency: { avg_latency_ms: number; p95_latency_ms: number };
  top_failure_steps: { step_name: string; provider?: string; failures: number }[];
  recent_failures: {
    metric_kind: string;
    step_name?: string | null;
    provider?: string | null;
    error?: string | null;
    created_at: string;
    entity_type?: string | null;
    entity_id?: string | null;
  }[];
};

export type AdminUserDetail = {
  user: AdminUserSummary;
  stories: AdminStorySummary[];
  recent_jobs: Array<Record<string, any>>;
  recent_activity: Array<Record<string, any>>;
};

export type GenerationJob = {
  id: string;
  entity_type: string;
  entity_id: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  total_steps: number;
  current_step: string;
  job_type?: string;
  error?: string;
  result?: Record<string, any>;
  started_at?: string;
  completed_at?: string;
  created_at: string;
};

export type GenerationCheckpoint = {
  id: string;
  story_id: string;
  job_id?: string | null;
  resume_job_id?: string | null;
  batch_number: number;
  batch_size: number;
  start_episode_number: number;
  start_scene_number: number;
  end_episode_number: number;
  end_scene_number: number;
  status: string;
  generation_version?: string | null;
  narration_model?: string | null;
  narration_voice?: string | null;
  narration_text?: string | null;
  audio_job_id?: string | null;
  audio_status?: string | null;
  narration_audio_url?: string | null;
  narration_audio_manifest_url?: string | null;
  state_snapshot?: Record<string, any> | null;
  resume_state?: Record<string, any> | null;
  reviewer_notes?: string | null;
  approved_at?: string | null;
  reviewed_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type HistoryEntry = {
  id: string;
  entity_type: "story" | "scene" | "checkpoint";
  entity_id: string;
  revision: number;
  event_type: string;
  workflow_version?: string | null;
  generation_version: string;
  source_job_id?: string | null;
  state_snapshot?: Record<string, any> | null;
  payload?: Record<string, any> | null;
  created_at: string;
};

export type GalleryItem = {
  id: string;
  kind: "scene" | "episode";
  media_kind?: "image" | "video";
  story_id: string;
  story_title: string;
  episode_id: string;
  episode_number: number;
  scene_id?: string | null;
  scene_number?: number | null;
  title: string;
  summary?: string | null;
  media_url: string;
  duration?: number | null;
  created_at: string;
};

export type UploadResponse = {
  url: string;
  key: string;
  content_type: string;
  size: number;
};

export type StoryAssistantResponse = {
  target: "story" | "scene";
  message: string;
  story_patch: Record<string, any>;
  scene_patch: Record<string, any>;
};

export type SocialAccount = {
  id: string;
  platform: "mock" | "youtube" | "tiktok";
  platform_user_id?: string | null;
  display_name?: string | null;
  scopes: string[];
  status: string;
  metadata: Record<string, any>;
  token_expires_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type PublishTarget = {
  id: string;
  platform: "mock" | "youtube" | "tiktok";
  social_account_id?: string | null;
  story_id?: string | null;
  episode_id?: string | null;
  scene_id?: string | null;
  artifact_id?: string | null;
  asset_kind: "episode" | "scene" | "artifact" | "external_url";
  media_url?: string | null;
  title: string;
  description: string;
  tags: string[];
  privacy_status: string;
  publish_mode: "manual" | "scheduled" | "auto_after_generation";
  requires_approval: boolean;
  approved_at?: string | null;
  scheduled_for?: string | null;
  status: string;
  error?: string | null;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
  posts?: PublishPost[];
};

export type PublishPost = {
  id: string;
  publish_target_id: string;
  platform: string;
  platform_post_id?: string | null;
  public_url?: string | null;
  upload_session_id?: string | null;
  status: string;
  response: Record<string, any>;
  error?: string | null;
  created_at: string;
  updated_at: string;
};

export type AutomationSchedule = {
  id: string;
  story_id?: string | null;
  name: string;
  schedule_type: "generate_only" | "publish_existing" | "generate_and_publish" | "series_continuation";
  cadence: "once" | "interval_hours" | "daily" | "weekly";
  cadence_config: Record<string, any>;
  timezone: string;
  next_run_at?: string | null;
  enabled: boolean;
  pipeline_config: Record<string, any>;
  publish_config: Record<string, any>;
  approval_policy: "require_approval" | "auto_publish" | "generate_only";
  status: string;
  last_run_at?: string | null;
  last_error?: string | null;
  created_at: string;
  updated_at: string;
};

export type ScheduledRun = {
  id: string;
  schedule_id?: string | null;
  story_id?: string | null;
  episode_id?: string | null;
  publish_target_id?: string | null;
  job_id?: string | null;
  run_type: string;
  due_at?: string | null;
  status: string;
  result: Record<string, any>;
  error?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
};

function resolvePipelineBase() {
  const explicit = import.meta.env.VITE_PIPELINE_API_BASE?.trim()?.replace(/\/+$/, "");
  if (explicit) return explicit;

  if (typeof window !== "undefined") {
    const { origin, hostname, port } = window.location;

    if (hostname.includes("localhost") || hostname === "127.0.0.1") {
      return `${origin.replace(/:5000$/, ":8000").replace(/:5173$/, ":8000")}/pipeline`;
    }

    const remapped = origin.replace("://5000-", "://8000-");
    if (remapped !== origin) {
      return `${remapped}/pipeline`;
    }

    if (port === "5000" || port === "5173") {
      return `${origin.replace(/:(5000|5173)$/, ":8000")}/pipeline`;
    }
  }

  return "/pipeline";
}

const BASE = resolvePipelineBase();
const AUTH_TOKEN_KEY = "storyforge_auth_token";

export function getAuthToken() {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(AUTH_TOKEN_KEY);
}

export function setAuthToken(token: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(AUTH_TOKEN_KEY, token);
}

export function clearAuthToken() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(AUTH_TOKEN_KEY);
}

async function req<T>(url: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers);
  const token = getAuthToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(url, { ...options, headers });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}

const json = (body: unknown) => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

const put = (body: unknown = {}) => ({
  method: "PUT",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

const ADMIN_AUTH_TOKEN_KEY = "storyforge_admin_auth_token";

export function getAdminAuthToken() {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ADMIN_AUTH_TOKEN_KEY);
}

export function setAdminAuthToken(token: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(ADMIN_AUTH_TOKEN_KEY, token);
}

export function clearAdminAuthToken() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ADMIN_AUTH_TOKEN_KEY);
}

async function adminReq<T>(url: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers);
  const token = getAdminAuthToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(url, { ...options, headers });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}

export const api = {
  register: (data: { email: string; password: string }) =>
    req<AuthResponse>(`${BASE}/auth/register`, json(data)),
  login: (data: { email: string; password: string }) =>
    req<AuthResponse>(`${BASE}/auth/login`, json(data)),
  me: () => req<User>(`${BASE}/auth/me`),
  logout: () => req<{ ok: boolean }>(`${BASE}/auth/logout`, { method: "POST" }),

  getStories: () => req<Story[]>(`${BASE}/stories`),
  getStory: (id: string) => req<Story>(`${BASE}/stories/${id}`),
  updateStory: (
    id: string,
    data: Partial<{
      title: string;
      prompt: string;
      genre: string;
      style: string;
      synopsis: string;
      setting: string;
      themes: string[];
    }>,
  ) => req<Story>(`${BASE}/stories/${id}`, put(data)),
  assistStory: (id: string, data: { instruction: string; target?: "story" | "scene"; scene_id?: string }) =>
    req<StoryAssistantResponse>(`${BASE}/stories/${id}/assistant`, json(data)),
  createStory: (data: {
    title: string;
    prompt: string;
    genre?: string;
    style?: string;
    frame_ratio?: string;
    num_episodes?: number;
    num_scenes?: number;
    workflow_type?: WorkflowType;
    bible_ids?: string[];
    style_reference_urls?: string[];
    character_reference_urls?: string[];
    scene_reference_urls?: string[];
  }) => req<Story>(`${BASE}/stories`, json(data)),
  approveOutline: (id: string) => req<Story>(`${BASE}/stories/${id}/approve-outline`, put()),
  generateStory: (id: string) => req<GenerationJob>(`${BASE}/stories/${id}/generate`, { method: "POST", body: "{}" }),

  getBibles: (storyId: string) => req<Bible[]>(`${BASE}/bibles/story/${storyId}`),
  createBible: (data: Partial<Bible>) => req<Bible>(`${BASE}/bibles`, json(data)),
  updateBible: (id: string, data: Partial<Bible>) => req<Bible>(`${BASE}/bibles/${id}`, { ...put(data), method: "PUT" }),
  deleteBible: (id: string) => req<{ deleted: string }>(`${BASE}/bibles/${id}`, { method: "DELETE" }),

  getCharacters: (storyId: string) => req<Character[]>(`${BASE}/characters/story/${storyId}`),
  approveCharacter: (id: string) => req<Character>(`${BASE}/characters/${id}/approve`, put()),
  lockCharacter: (id: string) => req<Character>(`${BASE}/characters/${id}/lock`, put()),
  regenerateCharacterRefs: (id: string) => req<GenerationJob>(`${BASE}/characters/${id}/regenerate-refs`, json({})),

  approveScene: (id: string) => req<Scene>(`${BASE}/scenes/${id}/approve`, put()),
  rejectScene: (id: string) => req<Scene>(`${BASE}/scenes/${id}/reject`, put()),
  lockScene: (id: string) => req<Scene>(`${BASE}/scenes/${id}/lock`, put()),
  regenerateScene: (id: string) => req<GenerationJob>(`${BASE}/scenes/${id}/regenerate`, json({})),
  updateScene: (
    id: string,
    data: Partial<{
      prompt: string;
      title: string;
      description: string;
      visual_prompt: string;
      mood: string;
      location: string;
      action: string;
      narration: string;
      duration: number;
      media_kind: string;
      frame_ratio: string;
      character_ids: string[];
      primary_character_ids: string[];
      reference_image_urls: string[];
      approval_status: string;
      locked: boolean;
    }>,
  ) => req<Scene>(`${BASE}/scenes/${id}`, put(data)),
  updateSceneReferences: (id: string, reference_image_urls: string[]) =>
    req<Scene>(`${BASE}/scenes/${id}/references`, json({ reference_image_urls })),

  getEpisodes: (storyId: string) => req<Episode[]>(`${BASE}/episodes/story/${storyId}`),
  getStoryCheckpoints: (storyId: string) => req<GenerationCheckpoint[]>(`${BASE}/stories/${storyId}/checkpoints`),
  approveCheckpoint: (storyId: string, checkpointId: string) => req<GenerationCheckpoint>(`${BASE}/stories/${storyId}/checkpoints/${checkpointId}/approve`, put()),
  getStoryHistory: (storyId: string) => req<HistoryEntry[]>(`${BASE}/stories/${storyId}/history`),
  getCheckpointHistory: (storyId: string, checkpointId: string) =>
    req<HistoryEntry[]>(`${BASE}/stories/${storyId}/checkpoints/${checkpointId}/history`),
  getSceneHistory: (sceneId: string) => req<HistoryEntry[]>(`${BASE}/scenes/${sceneId}/history`),
  getGallery: () => req<GalleryItem[]>(`${BASE}/gallery`),
  getPublicGallery: () => req<GalleryItem[]>(`${BASE}/gallery/public`),
  getJob: (jobId: string) => req<GenerationJob>(`${BASE}/jobs/${jobId}`),
  getEntityJobs: (type: string, id: string) => req<GenerationJob[]>(`${BASE}/jobs/entity/${type}/${id}`),
  uploadImage: async (file: File) => {
    const token = getAuthToken();
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${BASE}/uploads/image`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      body: form,
    });
    if (!res.ok) {
      const text = await res.text().catch(() => res.statusText);
      throw new Error(`API ${res.status}: ${text}`);
    }
    return res.json() as Promise<UploadResponse>;
  },

  getSocialAccounts: () => req<SocialAccount[]>(`${BASE}/social/accounts`),
  createMockSocialAccount: (data: Partial<SocialAccount> = {}) =>
    req<SocialAccount>(`${BASE}/social/accounts/mock`, json({ platform: "mock", ...data })),
  startSocialConnect: (platform: "youtube" | "tiktok") =>
    req<{ authorization_url: string; state: string }>(`${BASE}/social/${platform}/connect`, { method: "POST" }),
  disconnectSocialAccount: (accountId: string) => req<{ ok: boolean }>(`${BASE}/social/accounts/${accountId}`, { method: "DELETE" }),

  createPublishTarget: (data: Partial<PublishTarget> & { platform: "mock" | "youtube" | "tiktok"; title: string }) =>
    req<PublishTarget>(`${BASE}/publish-targets`, json(data)),
  getPublishTargets: () => req<PublishTarget[]>(`${BASE}/publish-targets`),
  getPublishTarget: (targetId: string) => req<PublishTarget>(`${BASE}/publish-targets/${targetId}`),
  approvePublishTarget: (targetId: string) => req<PublishTarget>(`${BASE}/publish-targets/${targetId}/approve`, { method: "POST" }),
  publishNow: (targetId: string) => req<{ job_id: string; publish_target_id: string }>(`${BASE}/publish-targets/${targetId}/publish-now`, { method: "POST" }),
  retryPublishTarget: (targetId: string) => req<{ job_id: string; publish_target_id: string }>(`${BASE}/publish-targets/${targetId}/retry`, { method: "POST" }),
  cancelPublishTarget: (targetId: string) => req<PublishTarget>(`${BASE}/publish-targets/${targetId}/cancel`, { method: "POST" }),

  createSchedule: (data: Partial<AutomationSchedule> & { name: string; schedule_type: AutomationSchedule["schedule_type"] }) =>
    req<AutomationSchedule>(`${BASE}/schedules`, json(data)),
  getSchedules: () => req<AutomationSchedule[]>(`${BASE}/schedules`),
  getSchedule: (scheduleId: string) => req<AutomationSchedule>(`${BASE}/schedules/${scheduleId}`),
  updateSchedule: (scheduleId: string, data: Partial<AutomationSchedule>) =>
    req<AutomationSchedule>(`${BASE}/schedules/${scheduleId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  deleteSchedule: (scheduleId: string) => req<{ ok: boolean }>(`${BASE}/schedules/${scheduleId}`, { method: "DELETE" }),
  runScheduleNow: (scheduleId: string) => req<{ scheduled_run: ScheduledRun }>(`${BASE}/schedules/${scheduleId}/run-now`, { method: "POST" }),
  dispatchDueSchedules: () => req<{ queued: Array<Record<string, any>> }>(`${BASE}/schedules/dispatch-due`, { method: "POST" }),
  getScheduleRuns: (scheduleId: string) => req<ScheduledRun[]>(`${BASE}/schedules/${scheduleId}/runs`),

  adminLogin: (data: { email: string; password: string }) => adminReq<AdminAuthResponse>(`${BASE}/admin/login`, json(data)),
  adminMe: () => adminReq<AdminProfile>(`${BASE}/admin/me`),
  adminLogout: () => adminReq<{ ok: boolean }>(`${BASE}/admin/logout`, { method: "POST" }),
  adminOverview: () => adminReq<AdminOverview>(`${BASE}/admin/overview`),
  adminUsers: () => adminReq<AdminUserSummary[]>(`${BASE}/admin/users`),
  adminUserDetail: (userId: string) => adminReq<AdminUserDetail>(`${BASE}/admin/users/${userId}`),
  adminUserStories: (userId: string) => adminReq<AdminStorySummary[]>(`${BASE}/admin/users/${userId}/stories`),
};
