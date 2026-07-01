export type Story = {
  id: string;
  title: string;
  prompt: string;
  genre: string;
  style: string;
  status: "draft" | "generating" | "completed" | "failed";
  episode_plan?: {
    synopsis: string;
    characters: any[];
    episodes: any[];
    setting: string;
    themes: string[];
  };
  created_at: string;
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
  created_at: string;
};

export type Episode = {
  id: string;
  story_id: string;
  episode_number: number;
  title: string;
  summary: string;
  status: string;
  scenes: Scene[];
};

export type Scene = {
  id: string;
  episode_id: string;
  scene_number: number;
  title: string;
  description: string;
  visual_prompt: string;
  video_url?: string;
  status: string;
  mood: string;
  location: string;
};

export type GenerationJob = {
  id: string;
  entity_type: string;
  entity_id: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  total_steps: number;
  current_step: string;
  error?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
};

const BASE_URL = "/pipeline";

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
  if (!res.ok) {
    throw new Error(`API error: ${res.statusText}`);
  }
  return res.json();
}

export const api = {
  getStories: () => fetchJson<Story[]>(`${BASE_URL}/stories`),
  createStory: (data: Partial<Story>) =>
    fetchJson<Story>(`${BASE_URL}/stories`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  getStory: (id: string) => fetchJson<Story>(`${BASE_URL}/stories/${id}`),
  generateStory: (id: string) =>
    fetchJson<GenerationJob>(`${BASE_URL}/stories/${id}/generate`, { method: "POST", body: "{}" }),
  getCharacters: (storyId: string) =>
    fetchJson<Character[]>(`${BASE_URL}/characters/story/${storyId}`),
  getEpisodes: (storyId: string) =>
    fetchJson<Episode[]>(`${BASE_URL}/episodes/story/${storyId}`),
  getJob: (jobId: string) => fetchJson<GenerationJob>(`${BASE_URL}/jobs/${jobId}`),
  getEntityJobs: (type: string, id: string) =>
    fetchJson<GenerationJob[]>(`${BASE_URL}/jobs/entity/${type}/${id}`),
};
