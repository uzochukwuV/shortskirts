const db = globalThis.__B44_DB__ || { auth:{ isAuthenticated: async()=>false, me: async()=>null }, entities:new Proxy({}, { get:()=>({ filter:async()=>[], get:async()=>null, create:async()=>({}), update:async()=>({}), delete:async()=>({}) }) }), integrations:{ Core:{ UploadFile:async()=>({ file_url:'' }) } } };

import { createClientFromRequest } from 'npm:@base44/sdk@0.8.40';
import { waitUntil } from 'base44:runtime';

export default async function(req) {
  try {
    const base44 = createClientFromRequest(req);

    const body = await req.json().catch(() => ({}));
    const videoId = (body.video_id || '').toString();
    const change = (body.change || '').toString().trim();
    if (!videoId || change.length < 2) {
      return Response.json({ error: 'video_id and a change description are required.' }, { status: 400 });
    }

    const video = await db.asServiceRole.entities.Video.get(videoId);
    if (!video) return Response.json({ error: 'Video not found.' }, { status: 404 });

    // Save the user's instruction
    const userMessage = await db.asServiceRole.entities.ChatMessage.create({
      video_id: videoId,
      role: 'user',
      content: change,
    });

    // Rewrite the prompt via LLM
    const llm = await db.asServiceRole.integrations.Core.InvokeLLM({
      prompt: `You are a cinematic AI video prompt engineer. The current video prompt is:\n"${video.prompt}"\n\nThe user wants this change applied:\n"${change}"\n\nRewrite the full video prompt to incorporate the change while keeping it vivid and cinematic. Return only the revised prompt text, no preamble.`,
      response_json_schema: {
        type: 'object',
        properties: { revised_prompt: { type: 'string' } },
        required: ['revised_prompt'],
      },
    });

    const revisedPrompt = (llm.revised_prompt || '').trim() || video.prompt;

    // Save the assistant's revised prompt
    const assistantMessage = await db.asServiceRole.entities.ChatMessage.create({
      video_id: videoId,
      role: 'assistant',
      content: revisedPrompt,
    });

    // Mark the video as generating with the new prompt
    await db.asServiceRole.entities.Video.update(videoId, { prompt: revisedPrompt, status: 'generating' });

    // Re-render in the background
    waitUntil((async () => {
      try {
        const fullPrompt = `${revisedPrompt}. ${video.motion_style} motion, ${video.camera_mode} camera, ${video.category} style, ${video.resolution} quality.`;
        const videoRes = await db.asServiceRole.integrations.Core.GenerateVideo({
          prompt: fullPrompt,
          aspect_ratio: video.aspect_ratio,
          duration: video.duration,
        });
        let thumbUrl = video.thumbnail_url;
        try {
          const img = await db.asServiceRole.integrations.Core.GenerateImage({
            prompt: `cinematic film still, ${revisedPrompt}, high detail, dramatic lighting`,
          });
          thumbUrl = img.url;
        } catch (_e) { /* keep existing thumbnail */ }
        await db.asServiceRole.entities.Video.update(videoId, {
          status: 'ready',
          video_url: videoRes.url,
          thumbnail_url: thumbUrl,
        });
      } catch (error) {
        await db.asServiceRole.entities.Video.update(videoId, { status: 'failed' }).catch(() => {});
      }
    })());

    return Response.json({ userMessage, assistantMessage, revisedPrompt });
  } catch (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }
}