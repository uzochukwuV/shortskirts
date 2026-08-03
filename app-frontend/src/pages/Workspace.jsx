import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, BookOpen, Bot, CheckCircle2, Hash, Loader2, Plus, Redo2, Send, Square, Undo2, Wrench, X } from 'lucide-react';
import { agentService } from '@/services/agentService';
import { storyService } from '@/services/storyService';

const panelTabs = [
  { id: 'ai', label: 'AI Tools' },
  { id: 'assets', label: 'Assets' },
  { id: 'settings', label: 'Settings' },
];

const initialMessage = {
  id: 'welcome',
  role: 'assistant',
  content: 'Tell me what you want to make. I can shape the story, revise scenes, manage references, and start generation when the plan is ready.',
};

export default function Workspace() {
  const navigate = useNavigate();
  const { storyId } = useParams();
  const [activeTab, setActiveTab] = useState('ai');
  const [mobileTab, setMobileTab] = useState('canvas');
  const [story, setStory] = useState(null);
  const [messages, setMessages] = useState([initialMessage]);
  const [conversationId, setConversationId] = useState(null);
  const [draft, setDraft] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (!storyId) return;
    storyService.get(storyId).then(setStory).catch((err) => setError(err.message || 'Unable to load this story.'));
  }, [storyId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSending]);

  const title = story?.title || 'New SonicVision project';
  const workflowStatus = story?.status || 'draft';
  const showCanvasOnMobile = mobileTab === 'canvas';
  const panelTab = showCanvasOnMobile ? activeTab : mobileTab;
  const canChat = Boolean(storyId) && !isSending;

  const sendMessage = async (event) => {
    event?.preventDefault();
    const message = draft.trim();
    if (!message || !storyId || isSending) return;
    setDraft('');
    setError('');
    setMessages((current) => [...current, { id: `user-${Date.now()}`, role: 'user', content: message }]);
    setIsSending(true);
    try {
      const response = await agentService.chat({
        message,
        story_id: storyId,
        conversation_id: conversationId || undefined,
        include_context: true,
      });
      if (response?.conversation_id) setConversationId(response.conversation_id);
      setMessages((current) => [...current, {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response?.message || 'I completed that step.',
        actions: response?.actions || [],
      }]);
      // Tool calls can mutate the outline, scenes, or workflow status.
      const refreshed = await storyService.get(storyId);
      setStory(refreshed);
    } catch (err) {
      setError(err?.message || 'The assistant could not complete that request.');
      setMessages((current) => [...current, {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'I could not complete that request. Check the connection and try again.',
        error: true,
      }]);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="h-screen bg-[#0a0a0a] flex flex-col overflow-hidden text-white">
      <header className="flex items-center justify-between px-3 sm:px-4 py-2.5 border-b border-white/5 bg-[#0a0a0a] z-30 flex-shrink-0">
        <div className="flex items-center gap-2 sm:gap-3 min-w-0">
          <button onClick={() => navigate('/dashboard')} className="text-white/60 hover:text-white flex-shrink-0" aria-label="Back to dashboard"><ArrowLeft size={18} /></button>
          <div className="flex items-center gap-2 min-w-0"><div className="w-5 h-5 bg-[#dfff1e] rounded flex-shrink-0" /><span className="text-xs sm:text-sm text-white/80 truncate">{title}</span></div>
        </div>
        <div className="hidden md:flex items-center gap-2">
          {panelTabs.map((tab) => <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`px-3 py-1.5 rounded-full text-xs font-medium transition ${activeTab === tab.id ? 'bg-[#dfff1e] text-black' : 'text-white/60 hover:text-white bg-white/5'}`}>{tab.label}</button>)}
        </div>
        <div className="flex items-center gap-2 text-white/60"><button className="hidden sm:inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-white/5 hover:bg-white/10 transition text-xs"><Undo2 size={14} /> Undo</button><button className="hidden sm:inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-white/5 hover:bg-white/10 transition text-xs"><Redo2 size={14} /> Redo</button></div>
      </header>

      <div className="md:hidden grid grid-cols-4 gap-2 px-3 py-2 border-b border-white/5 bg-[#0a0a0a]">
        {[{ id: 'canvas', label: 'Canvas', icon: Square }, ...panelTabs.map((tab) => ({ id: tab.id, label: tab.label, icon: tab.id === 'ai' ? Bot : tab.id === 'assets' ? BookOpen : Hash }))].map((tab) => { const Icon = tab.icon; const active = mobileTab === tab.id; return <button key={tab.id} onClick={() => setMobileTab(tab.id)} className={`flex items-center justify-center gap-1 rounded-full px-2 py-2 text-xs font-medium transition ${active ? 'bg-[#dfff1e] text-black' : 'bg-white/5 text-white/60'}`}><Icon size={14} /> {tab.label}</button>; })}
      </div>

      <div className="flex-1 min-h-0 grid grid-cols-1 md:grid-cols-[1fr_320px] lg:grid-cols-[1fr_380px]">
        {(showCanvasOnMobile || window.innerWidth >= 768) && <main className="relative min-h-0 overflow-hidden bg-[radial-gradient(circle_at_center,_rgba(255,255,255,0.06)_1px,_transparent_1px)] [background-size:24px_24px]"><div className="absolute inset-0 flex items-center justify-center p-6"><div className="w-full max-w-3xl rounded-3xl border border-white/10 bg-white/5 backdrop-blur-sm p-6 shadow-2xl"><div className="flex items-center justify-between mb-4 text-white/60 text-sm"><span>Frame 1</span><button className="inline-flex items-center gap-1 rounded-full bg-white/5 px-3 py-1.5 hover:bg-white/10 transition"><Plus size={14} /> Add frame</button></div><div className="aspect-video rounded-2xl border border-white/10 bg-black/20 flex items-center justify-center text-white/30 text-sm">{story?.episode_plan ? 'Outline ready — use the assistant to shape your scenes.' : 'Your generated scenes will appear here.'}</div></div></div></main>}
        <aside className={`${showCanvasOnMobile ? 'hidden md:block' : 'block'} min-h-0 border-l border-white/5 bg-[#111111] overflow-hidden`}>
          {panelTab === 'ai' && <ChatPanel messages={messages} draft={draft} setDraft={setDraft} sendMessage={sendMessage} isSending={isSending} error={error} canChat={canChat} status={workflowStatus} messagesEndRef={messagesEndRef} />}
          {panelTab === 'assets' && <Panel label="Assets" description="Reference images, generated clips, and story assets will appear here." />}
          {panelTab === 'settings' && <Panel label="Settings" description="Project configuration, model selection, and output controls." />}
        </aside>
      </div>
    </div>
  );
}

function ChatPanel({ messages, draft, setDraft, sendMessage, isSending, error, canChat, status, messagesEndRef }) {
  return <div className="h-full flex flex-col"><div className="px-4 py-4 border-b border-white/5 flex-shrink-0"><div className="flex items-center justify-between"><div><p className="text-xs uppercase tracking-[0.2em] text-white/40">Production assistant</p><h2 className="mt-1 text-lg font-semibold">Build with SonicVision</h2></div><span className="text-[10px] uppercase tracking-wider text-[#dfff1e] bg-[#dfff1e]/10 rounded-full px-2 py-1">{status}</span></div></div><div className="flex-1 min-h-0 overflow-y-auto px-4 py-4 space-y-4"><div className="flex gap-2 text-xs text-white/40"><Bot size={14} className="text-[#dfff1e] mt-0.5" /> I can call production tools as we work.</div>{messages.map((message) => <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}><div className={`max-w-[92%] rounded-2xl px-3 py-2.5 text-sm leading-relaxed ${message.role === 'user' ? 'bg-[#dfff1e] text-black rounded-br-md' : message.error ? 'bg-red-500/10 text-red-200 border border-red-500/20' : 'bg-white/5 text-white/80 border border-white/5 rounded-bl-md'}`}><p className="whitespace-pre-wrap">{message.content}</p>{message.actions?.length > 0 && <div className="mt-3 space-y-1.5 border-t border-white/10 pt-2">{message.actions.map((action, index) => <div key={`${action.tool}-${index}`} className="flex items-center gap-1.5 text-[11px] text-white/50"><Wrench size={11} className="text-[#dfff1e]" /> {action.tool}{action.error ? <X size={11} className="text-red-300" /> : <CheckCircle2 size={11} className="text-emerald-300" />}</div>)}</div>}</div></div>)}{isSending && <div className="flex items-center gap-2 text-xs text-white/50"><Loader2 size={14} className="animate-spin text-[#dfff1e]" /> SonicVision is working…</div>}<div ref={messagesEndRef} /></div>{error && <p className="px-4 pb-2 text-xs text-red-300">{error}</p>}<form onSubmit={sendMessage} className="p-3 border-t border-white/5 flex-shrink-0"><textarea value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); sendMessage(event); } }} disabled={!canChat} rows={3} placeholder={canChat ? 'Describe a scene, revise the outline, or ask me to generate…' : 'Create or open a story to start chatting…'} className="w-full resize-none rounded-2xl border border-white/10 bg-white/5 px-3 py-3 text-sm text-white placeholder:text-white/30 outline-none focus:border-[#dfff1e]/50 disabled:opacity-50" /><div className="mt-2 flex items-center justify-between"><span className="text-[11px] text-white/35">Enter to send · Shift+Enter for a new line</span><button type="submit" disabled={!canChat || !draft.trim()} className="w-9 h-9 rounded-full bg-[#dfff1e] text-black flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed"><Send size={15} /></button></div></form></div>;
}

function Panel({ label, description }) { return <div className="p-5 space-y-4"><div><p className="text-xs uppercase tracking-[0.2em] text-white/40">{label}</p><h2 className="mt-2 text-xl font-semibold text-white">{label}</h2><p className="mt-2 text-sm text-white/60 leading-relaxed">{description}</p></div><div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-white/50">This panel will update as your production develops.</div></div>; }