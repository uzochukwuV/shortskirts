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
  status: "draft" | "approved" | "generating" | "completed" | "ready" | "failed";
  approval_status: "pending_approval" | "approved";
  workflow_type: WorkflowType;
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
  video_url?: string;
  exit_frame_url?: string;
  duration?: number;
  status: string;
  approval_status: "pending" | "approved" | "rejected" | "locked";
  locked: boolean;
  regeneration_count: number;
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

const BASE = import.meta.env.VITE_PIPELINE_API_BASE?.trim()?.replace(/\/+$/, "") || "/pipeline";
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

export const api = {
  register: (data: { email: string; password: string }) =>
    req<AuthResponse>(`${BASE}/auth/register`, json(data)),
  login: (data: { email: string; password: string }) =>
    req<AuthResponse>(`${BASE}/auth/login`, json(data)),
  me: () => req<User>(`${BASE}/auth/me`),
  logout: () => req<{ ok: boolean }>(`${BASE}/auth/logout`, { method: "POST" }),

  getStories: () => req<Story[]>(`${BASE}/stories`),
  getStory: (id: string) => req<Story>(`${BASE}/stories/${id}`),
  createStory: (data: {
    title: string;
    prompt: string;
    genre?: string;
    style?: string;
    num_episodes?: number;
    num_scenes?: number;
    workflow_type?: WorkflowType;
    bible_ids?: string[];
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

  getEpisodes: (storyId: string) => req<Episode[]>(`${BASE}/episodes/story/${storyId}`),
  getGallery: () => req<GalleryItem[]>(`${BASE}/gallery`),
  getPublicGallery: () => req<GalleryItem[]>(`${BASE}/gallery/public`),
  getJob: (jobId: string) => req<GenerationJob>(`${BASE}/jobs/${jobId}`),
  getEntityJobs: (type: string, id: string) => req<GenerationJob[]>(`${BASE}/jobs/entity/${type}/${id}`),
};
