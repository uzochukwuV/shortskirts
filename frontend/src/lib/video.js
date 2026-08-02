const db = globalThis.__B44_DB__ || { auth:{ isAuthenticated: async()=>false, me: async()=>null }, entities:new Proxy({}, { get:()=>({ filter:async()=>[], get:async()=>null, create:async()=>({}), update:async()=>({}), delete:async()=>({}) }) }), integrations:{ Core:{ UploadFile:async()=>({ file_url:'' }) } } };


export const CATEGORIES = [
  { id: "all", label: "All" },
  { id: "cinematic", label: "Cinematic" },
  { id: "portrait", label: "Portrait" },
  { id: "product", label: "Product" },
  { id: "landscape", label: "Landscape" },
  { id: "abstract", label: "Abstract" },
  { id: "fashion", label: "Fashion" },
  { id: "travel", label: "Travel" },
];

export const ASPECT_RATIOS = ["16:9", "9:16", "1:1"];
export const RESOLUTIONS = ["720p", "1080p", "4K"];
export const DURATIONS = [4, 6, 8];
export const MOTION_STYLES = ["smooth", "dynamic", "slow", "fast", "cinematic"];
export const CAMERA_MODES = ["static", "dolly", "orbit", "crane", "handheld"];

export const PROMPT_SUGGESTIONS = [
  "A neon-lit Tokyo street in the rain at midnight",
  "A lone astronaut walking across a red desert planet",
  "Slow-motion coffee pouring into a glass cup, macro",
  "Golden hour over rolling vineyards, drone shot",
  "A fashion model walking through a gallery of mirrors",
];

export async function createVideo(payload) {
  const res = await db.functions.invoke("generateVideo", payload);
  return res.data.video;
}

export async function refineVideo(video_id, change) {
  const res = await db.functions.invoke("refineVideo", { video_id, change });
  return res.data;
}