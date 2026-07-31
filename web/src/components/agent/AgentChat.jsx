import { useState, useRef, useEffect, useCallback } from "react";
import {
  createAgentConversation,
  deleteAgentConversation,
  agentChatStream,
  agentChatStreamNew,
  pollJobStatus,
  listAgentTools,
} from "@/api/dysentryClient";
import { SparklesIcon, SendIcon, TrashIcon, XIcon, LoaderIcon, CheckCircleIcon, XCircleIcon, ClockIcon } from "lucide-react";

export default function AgentChat({ storyId, onClose }) {
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tools, setTools] = useState([]);
  const [activeJobs, setActiveJobs] = useState(new Map()); // jobId -> status
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const abortControllerRef = useRef(null);

  // Load tools on mount
  useEffect(() => {
    listAgentTools()
      .then((data) => setTools(data.tools || []))
      .catch(console.error);
  }, []);

  // Add welcome message when starting
  const startConversation = useCallback(() => {
    setMessages([
      {
        role: "assistant",
        content: `Hello! I'm your AI production assistant for this story. I can help you:

• Create and edit scenes with detailed prompts
• Manage continuity between scenes
• Generate and regenerate content
• Set up character references
• Answer questions about your production

When I create scenes, I'll show you the generation job status in real-time. What would you like to do?`,
      },
    ]);
  }, []);

  // Stream chat response
  const streamMessage = useCallback(async (convId, userMessage) => {
    // Add user message
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    
    // Add empty assistant message that we'll update
    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        content: "",
        actions: [],
        isStreaming: true,
      },
    ]);
    
    const assistantMsgIndex = messages.length + 1;
    const abortController = new AbortController();
    abortControllerRef.current = abortController;
    
    try {
      const streamFn = convId ? agentChatStream : agentChatStreamNew;
      const stream = convId 
        ? streamFn(convId, userMessage)
        : streamFn(userMessage, storyId);
      
      const reader = stream.body.getReader();
      const decoder = new TextDecoder();
      let currentToolId = null;
      let pendingToolResult = null;
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");
        
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          
          try {
            const data = JSON.parse(line.slice(6));
            
            if (data.type === "message") {
              // Update assistant message content
              setMessages((prev) => {
                const updated = [...prev];
                if (updated[assistantMsgIndex]) {
                  updated[assistantMsgIndex] = {
                    ...updated[assistantMsgIndex],
                    content: data.content,
                  };
                }
                return updated;
              });
            } else if (data.type === "tool_start") {
              currentToolId = data.id;
              // Add tool action to the assistant message
              setMessages((prev) => {
                const updated = [...prev];
                if (updated[assistantMsgIndex]) {
                  updated[assistantMsgIndex] = {
                    ...updated[assistantMsgIndex],
                    actions: [
                      ...updated[assistantMsgIndex].actions,
                      {
                        tool: data.tool,
                        arguments: data.arguments,
                        status: "running",
                        id: data.id,
                      },
                    ],
                  };
                }
                return updated;
              });
            } else if (data.type === "tool_complete") {
              const result = data.result;
              
              // Check if result contains a job_id for polling
              const jobId = result?.result?.job_id;
              
              // Update tool action status
              setMessages((prev) => {
                const updated = [...prev];
                if (updated[assistantMsgIndex]) {
                  updated[assistantMsgIndex] = {
                    ...updated[assistantMsgIndex],
                    actions: updated[assistantMsgIndex].actions.map((action) =>
                      action.id === data.id
                        ? { ...action, status: "complete", result: result.result }
                        : action
                    ),
                  };
                }
                return updated;
              });
              
              // If there's a job_id, start polling for status
              if (jobId) {
                setActiveJobs((prev) => new Map(prev).set(jobId, { status: "pending", toolId: data.id }));
                
                // Poll job status
                pollJobStatus(
                  jobId,
                  (job) => {
                    setActiveJobs((prev) => {
                      const updated = new Map(prev);
                      updated.set(jobId, { ...updated.get(jobId), ...job });
                      return updated;
                    });
                  },
                  3000 // 3 second interval
                ).then(() => {
                  // Job completed
                  setActiveJobs((prev) => {
                    const updated = new Map(prev);
                    updated.delete(jobId);
                    return updated;
                  });
                }).catch((err) => {
                  console.error("Job polling error:", err);
                  setActiveJobs((prev) => {
                    const updated = new Map(prev);
                    updated.delete(jobId);
                    return updated;
                  });
                });
              }
            } else if (data.type === "tool_error") {
              setMessages((prev) => {
                const updated = [...prev];
                if (updated[assistantMsgIndex]) {
                  updated[assistantMsgIndex] = {
                    ...updated[assistantMsgIndex],
                    actions: updated[assistantMsgIndex].actions.map((action) =>
                      action.id === data.id
                        ? { ...action, status: "error", error: data.error }
                        : action
                    ),
                  };
                }
                return updated;
              });
            } else if (data.type === "done") {
              setMessages((prev) => {
                const updated = [...prev];
                if (updated[assistantMsgIndex]) {
                  updated[assistantMsgIndex] = {
                    ...updated[assistantMsgIndex],
                    content: data.message || updated[assistantMsgIndex].content,
                    isStreaming: false,
                  };
                }
                return updated;
              });
            } else if (data.type === "error") {
              setError(data.message);
            }
          } catch (e) {
            console.error("Failed to parse SSE data:", e);
          }
        }
      }
      
      // Get conversation ID from headers if new
      if (!convId) {
        // Conversation ID should be in the URL or we need to extract it
        // For now, we'll rely on the session
      }
      
    } catch (err) {
      if (err.name !== "AbortError") {
        setError(err.message || "Stream failed");
        // Remove failed assistant message
        setMessages((prev) => prev.slice(0, -1));
      }
    } finally {
      setLoading(false);
      abortControllerRef.current = null;
    }
  }, [storyId, messages.length]);

  // Send a message
  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");
    setLoading(true);
    setError(null);

    // Start conversation if needed
    let convId = conversationId;
    if (!convId && messages.length === 0) {
      try {
        const result = await createAgentConversation(storyId);
        convId = result.conversation_id;
        setConversationId(convId);
      } catch (err) {
        setError(err.message || "Failed to start conversation");
        setLoading(false);
        return;
      }
    }

    await streamMessage(convId, userMessage);
  };

  // Delete conversation and start fresh
  const clearConversation = async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    if (conversationId) {
      try {
        await deleteAgentConversation(conversationId);
      } catch (e) {
        console.error("Failed to delete conversation:", e);
      }
    }
    setConversationId(null);
    setMessages([]);
    setActiveJobs(new Map());
    setError(null);
    startConversation();
  };

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, activeJobs]);

  // Focus input when component mounts
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Start conversation on mount
  useEffect(() => {
    if (storyId && messages.length === 0) {
      startConversation();
    }
  }, [storyId]);

  return (
    <div className="flex flex-col h-full bg-gray-900 border-l border-gray-700">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 bg-gray-800">
        <div className="flex items-center gap-2">
          <SparklesIcon className="w-5 h-5 text-purple-400" />
          <span className="font-medium text-gray-100">AI Assistant</span>
        </div>
        <div className="flex items-center gap-2">
          {conversationId && (
            <button
              onClick={clearConversation}
              className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-gray-700 rounded"
              title="Clear conversation"
            >
              <TrashIcon className="w-4 h-4" />
            </button>
          )}
          {onClose && (
            <button
              onClick={onClose}
              className="p-1.5 text-gray-400 hover:text-gray-200 hover:bg-gray-700 rounded"
            >
              <XIcon className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Active Jobs Banner */}
      {activeJobs.size > 0 && (
        <div className="px-4 py-2 bg-blue-900/30 border-b border-blue-800">
          <div className="flex items-center gap-2 text-sm">
            <LoaderIcon className="w-4 h-4 text-blue-400 animate-spin" />
            <span className="text-blue-300">
              {activeJobs.size} generation job{activeJobs.size > 1 ? "s" : ""} in progress
            </span>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] rounded-lg px-4 py-3 ${
                msg.role === "user"
                  ? "bg-purple-600 text-white"
                  : "bg-gray-800 text-gray-100 border border-gray-700"
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
              
              {/* Streaming indicator */}
              {msg.isStreaming && (
                <span className="inline-block w-2 h-2 ml-1 bg-purple-400 rounded-full animate-pulse" />
              )}
              
              {/* Tool actions */}
              {msg.actions && msg.actions.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-600">
                  <p className="text-xs text-gray-400 mb-2">Actions:</p>
                  <div className="space-y-2">
                    {msg.actions.map((action, j) => (
                      <div key={j} className="text-xs bg-gray-900/50 rounded p-2">
                        <div className="flex items-center gap-2">
                          <span className="text-purple-300 font-medium">{action.tool}</span>
                          {action.status === "running" && (
                            <LoaderIcon className="w-3 h-3 text-yellow-400 animate-spin" />
                          )}
                          {action.status === "complete" && (
                            <CheckCircleIcon className="w-3 h-3 text-green-400" />
                          )}
                          {action.status === "error" && (
                            <XCircleIcon className="w-3 h-3 text-red-400" />
                          )}
                        </div>
                        
                        {/* Job status if applicable */}
                        {action.result?.job_id && (
                          <div className="mt-1 flex items-center gap-1">
                            <ClockIcon className="w-3 h-3 text-gray-500" />
                            <span className="text-gray-400">
                              Job: {action.result.job_id.slice(0, 8)}...
                            </span>
                            <span className="text-gray-500">
                              (poll with {action.result.poll_url})
                            </span>
                          </div>
                        )}
                        
                        {action.error && (
                          <p className="text-red-400 mt-1">{action.error}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && messages.length > 0 && messages[messages.length - 1]?.role !== "user" && (
          <div className="flex justify-start">
            <div className="bg-gray-800 text-gray-100 border border-gray-700 rounded-lg px-4 py-3">
              <div className="flex items-center gap-2">
                <LoaderIcon className="w-4 h-4 text-purple-400 animate-spin" />
                <span className="text-gray-400">Processing...</span>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="flex justify-center">
            <div className="bg-red-900/50 text-red-300 border border-red-700 rounded-lg px-4 py-2">
              {error}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-gray-700 bg-gray-800">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            sendMessage();
          }}
          className="flex gap-2"
        >
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask me to create scenes, modify scripts..."
            disabled={loading}
            className="flex-1 bg-gray-700 text-white placeholder-gray-400 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <SendIcon className="w-5 h-5" />
          </button>
        </form>
        <p className="text-xs text-gray-500 mt-2">
          {tools.length} tools available • Real-time streaming
        </p>
      </div>
    </div>
  );
}
