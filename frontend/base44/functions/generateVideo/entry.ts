const db = globalThis.__B44_DB__ || { auth:{ isAuthenticated: async()=>false, me: async()=>null }, entities:new Proxy({}, { get:()=>({ filter:async()=>[], get:async()=>null, create:async()=>({}), update:async()=>({}), delete:async()=>({}) }) }), integrations:{ Core:{ UploadFile:async()=>({ file_url:'' }) } } };

import { createClientFromRequest } from 'npm:@base44/sdk@0.8.40';
import { waitUntil } from 'base44:runtime';

const ALLOWED = {
  category: ["cinematic", "portrait", "product", "landscape", "abstract", "fashion", "travel"],
  aspect_ratio: ["16:9", "9:16", "1:1"],
  resolution: ["720p", "1080p", "4K"],
  duration: [4, 6, 8],
  motion_style: ["smooth", "dynamic", "slow", "fast", "cinematic"],
  camera_mode: ["static", "dolly", "orbit", "crane", "handheld"],
};

function pick(value, key, fallback) {
  return ALLOWED[key].includes(value) ? value : fallback;
}

export default async function(req) {
  try {
    const base44 = createClientFromRequest(req);

    const body = await req.json().catch(() => ({}));
    const prompt = (body.prompt || '').toString().trim();
    if (!prompt || prompt.length < 3) {
      return Response.json({ error: 'A prompt of at least 3 characters is required.' }, { status: 400 });
    }
    if (prompt.length > 600) {
      return Response.json({ error: 'Prompt is too long (max 600 characters).' }, { status: 400 });
    }

    const videoId = body.video_id || null;
    const settings = {
      category: pick(body.category, 'category', 'cinematic'),
      aspect_ratio: pick(body.aspect_ratio, 'aspect_ratio', '16:9'),
      resolution: pick(body.resolution, 'resolution', '1080p'),
      duration: ALLOWED.duration.includes(Number(body.duration)) ? Number(body.duration) : 6,
      motion_style: pick(body.motion_style, 'motion_style', 'cinematic'),
      camera_mode: pick(body.camera_mode, 'camera_mode', 'dolly'),
    };

    let video;
    if (videoId) {
      // Re-render an existing video with an updated prompt
      video = await db.asServiceRole.entities.Video.get(videoId);
      await db.asServiceRole.entities.Video.update(videoId, { prompt, status: 'generating', ...settings });
      video = { ...video, prompt, status: 'generating', ...settings };
    } else {
      video = await db.asServiceRole.entities.Video.create({ prompt, status: 'generating', ...settings });
    }

    const id = video.id;

    // Complete generation in the background; the Generate page tracks the record.
    waitUntil((async () => {
      try {
        const fullPrompt = `${prompt}. ${settings.motion_style} motion, ${settings.camera_mode} camera, ${settings.category} style, ${settings.resolution} quality.`;
        const videoRes = await db.asServiceRole.integrations.Core.GenerateVideo({
          prompt: fullPrompt,
          aspect_ratio: settings.aspect_ratio,
          duration: settings.duration,
        });
        let thumbUrl = null;
        try {
          const img = await db.asServiceRole.integrations.Core.GenerateImage({
            prompt: `cinematic film still, ${prompt}, high detail, dramatic lighting`,
          });
          thumbUrl = img.url;
        } catch (_e) { /* thumbnail optional */ }
        await db.asServiceRole.entities.Video.update(id, {
          status: 'ready',
          video_url: videoRes.url,
          thumbnail_url: thumbUrl,
        });
      } catch (error) {
        await db.asServiceRole.entities.Video.update(id, { status: 'failed' }).catch(() => {});
      }
    })());

    return Response.json({ video });
  } catch (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }
}