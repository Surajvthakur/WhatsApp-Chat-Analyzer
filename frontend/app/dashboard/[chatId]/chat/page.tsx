"use client";

import { use } from "react";
import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { 
  getChatHistory, 
  addChatMessage, 
  ChatMessage 
} from "@/lib/api";
import { 
  Send, 
  Bot, 
  User, 
  Loader2, 
  Sparkles, 
  MessageSquare, 
  FileText,
  Clock,
  Info
} from "lucide-react";

interface ChatPageProps {
  params: Promise<{ chatId: string }>;
}

export default function ChatPage({ params }: ChatPageProps) {
  const { chatId } = use(params);
  const [isInitializing, setIsInitializing] = useState(true);
  const [initError, setInitError] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSavedWorkspace, setIsSavedWorkspace] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const getAuthHeaders = (): Record<string, string> => {
    if (typeof window === "undefined") return {};
    const token = localStorage.getItem("auth_token");
    return token ? { Authorization: `Bearer ${token}` } : {};
  };

  // Sample prompt suggestions
  const suggestions = [
    { text: "Summarize this WhatsApp chat", icon: FileText },
    { text: "Who are the most active people and when do they chat?", icon: Clock },
    { text: "What are the most common emojis used?", icon: Sparkles },
    { text: "What are the main topics of conversation?", icon: MessageSquare },
  ];

  // Initialize session when page mounts
  useEffect(() => {
    let active = true;
    const initSession = async () => {
      setIsInitializing(true);
      setInitError("");
      try {
        // 1. Initialize FastAPI RAM session
        const res = await fetch(`${baseUrl}/api/v1/ai/${chatId}/init`, {
          method: "POST",
          headers: getAuthHeaders(),
        });
        if (!res.ok) {
          throw new Error("Failed to initialize AI session");
        }
        
        // 2. Fetch persistent message history from database
        try {
          const dbMessages = await getChatHistory(chatId);
          if (active) {
            setIsSavedWorkspace(true);
            if (dbMessages.length > 0) {
              setMessages(dbMessages);
            } else {
              setMessages([
                {
                  role: "assistant",
                  content: "Hi! I've loaded your WhatsApp chat into my memory. Ask me anything about it!",
                },
              ]);
            }
          }
        } catch (dbErr) {
          // If history fetch fails with 404, it means it is a temporary/draft workspace
          if (active) {
            setIsSavedWorkspace(false);
            setMessages([
              {
                role: "assistant",
                content: "Hi! I've loaded your WhatsApp chat into my memory. Ask me anything about it!",
              },
            ]);
          }
        }
      } catch (err: any) {
        if (active) {
          setInitError(err.message || "Something went wrong.");
        }
      } finally {
        if (active) {
          setIsInitializing(false);
        }
      }
    };

    initSession();

    return () => {
      active = false;
      // Close session on unmount
      fetch(`${baseUrl}/api/v1/ai/${chatId}/close`, {
        method: "DELETE",
        headers: getAuthHeaders(),
        keepalive: true,
      }).catch((err) => console.error("Failed to close AI session", err));
    };
  }, [chatId, baseUrl]);

  // Handle unload (tab close)
  useEffect(() => {
    const handleBeforeUnload = () => {
      fetch(`${baseUrl}/api/v1/ai/${chatId}/close`, {
        method: "DELETE",
        headers: getAuthHeaders(),
        keepalive: true,
      });
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, [chatId, baseUrl]);

  // Auto scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (textToSend: string) => {
    if (!textToSend.trim() || isLoading) return;

    const userMessage = textToSend.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setIsLoading(true);

    // Save user message to database asynchronously if it is a saved workspace
    if (isSavedWorkspace) {
      addChatMessage(chatId, "user", userMessage).catch((err) =>
        console.error("Failed to save user message to DB", err)
      );
    }

    try {
      const res = await fetch(`${baseUrl}/api/v1/ai/${chatId}/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeaders(),
        },
        body: JSON.stringify({ question: userMessage }),
      });

      if (!res.ok) {
        throw new Error("Failed to get answer");
      }

      const data = await res.json();
      const assistantAnswer = data.answer;
      
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: assistantAnswer },
      ]);

      // Save assistant response to database asynchronously if it is a saved workspace
      if (isSavedWorkspace) {
        addChatMessage(chatId, "assistant", assistantAnswer).catch((err) =>
          console.error("Failed to save assistant message to DB", err)
        );
      }
    } catch (err: any) {
      const errResponse = "Sorry, I couldn't process that request right now. Please try again.";
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: errResponse,
        },
      ]);

      if (isSavedWorkspace) {
        addChatMessage(chatId, "assistant", errResponse).catch((dbErr) =>
          console.error("Failed to save assistant error message to DB", dbErr)
        );
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleSuggestionClick = (text: string) => {
    handleSubmit(text);
  };

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col rounded-2xl border border-[var(--border)] bg-[var(--card)] shadow-md overflow-hidden animate-in fade-in duration-300">
      {/* Chat Header */}
      <div className="flex items-center justify-between border-b border-[var(--border)] px-6 py-4 bg-[var(--muted)]/20">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--primary)]/10 text-[var(--primary)]">
            <Bot className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-base font-bold text-[var(--foreground)]">Ask AI Chat Assistant</h2>
            <p className="text-xs text-[var(--muted-foreground)]">
              Semantic analysis & insights on your uploaded WhatsApp conversation
            </p>
          </div>
        </div>
      </div>

      {/* Chat Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-[var(--card)]">
        {isInitializing ? (
          <div className="flex h-full flex-col items-center justify-center text-center p-8">
            <Loader2 className="h-10 w-10 animate-spin text-[var(--primary)] mb-4" />
            <p className="text-lg font-bold text-[var(--foreground)]">Initializing AI Engine...</p>
            <p className="text-sm text-[var(--muted-foreground)] mt-2 max-w-md leading-relaxed">
              We are compiling and indexing your conversation data to enable high-speed AI retrieval. This will take only a brief moment...
            </p>
          </div>
        ) : initError ? (
          <div className="flex h-full flex-col items-center justify-center p-8 text-center">
            <p className="text-red-500 mb-2 font-bold">Initialization Failed</p>
            <p className="text-sm text-[var(--muted-foreground)]">{initError}</p>
            <Button onClick={() => window.location.reload()} className="mt-4">
              Retry Connection
            </Button>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Draft Notification Banner */}
            {!isSavedWorkspace && (
              <div className="flex items-center gap-2 rounded-xl bg-amber-500/10 border border-amber-500/20 px-4 py-2.5 text-xs text-amber-600 font-semibold mb-4 mx-auto max-w-xl justify-center animate-in slide-in-from-top duration-300">
                <Info className="h-4 w-4 shrink-0 text-amber-500" />
                <span>Draft Session: Click "Save Workspace" on the Analytics page to keep this chat history persistently.</span>
              </div>
            )}

            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex gap-4 ${
                  msg.role === "user" ? "justify-end animate-in slide-in-from-right duration-200" : "justify-start animate-in slide-in-from-left duration-200"
                }`}
              >
                {msg.role === "assistant" && (
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[var(--primary)]/10 text-[var(--primary)] mt-0.5">
                    <Bot className="h-5 w-5" />
                  </div>
                )}
                
                <div
                  className={`flex max-w-[75%] flex-col rounded-2xl px-4.5 py-3 shadow-2xs ${
                    msg.role === "user"
                      ? "bg-[var(--primary)] text-[var(--primary-foreground)] rounded-tr-none"
                      : "bg-[var(--muted)]/50 text-[var(--foreground)] rounded-tl-none border border-[var(--border)]/30"
                  }`}
                >
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">
                    {msg.content}
                  </p>
                </div>

                {msg.role === "user" && (
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[var(--muted)] text-[var(--muted-foreground)] mt-0.5">
                    <User className="h-5 w-5" />
                  </div>
                )}
              </div>
            ))}
            
            {isLoading && (
              <div className="flex gap-4 justify-start animate-pulse">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[var(--primary)]/10 text-[var(--primary)]">
                  <Bot className="h-5 w-5" />
                </div>
                <div className="flex items-center gap-3 rounded-2xl bg-[var(--muted)]/50 border border-[var(--border)]/30 px-4.5 py-3 text-[var(--foreground)] rounded-tl-none">
                  <Loader2 className="h-4 w-4 animate-spin text-[var(--primary)]" />
                  <span className="text-sm font-semibold">Thinking...</span>
                </div>
              </div>
            )}
            
            {messages.length <= 1 && !isLoading && (
              <div className="pt-6 animate-in fade-in zoom-in duration-300">
                <div className="text-center mb-6">
                  <p className="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                    Or select a suggested query to get started
                  </p>
                </div>
                <div className="grid gap-4 sm:grid-cols-2 max-w-2xl mx-auto">
                  {suggestions.map((sug, i) => {
                    const Icon = sug.icon;
                    return (
                      <Card 
                        key={i} 
                        className="cursor-pointer border-[var(--border)] hover:border-[var(--primary)] hover:bg-[var(--primary)]/5 transition-all duration-200"
                        onClick={() => handleSuggestionClick(sug.text)}
                      >
                        <CardContent className="flex items-center gap-3 p-4">
                          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--primary)]/10 text-[var(--primary)]">
                            <Icon className="h-4.5 w-4.5" />
                          </div>
                          <span className="text-xs font-semibold text-[var(--foreground)] leading-tight">
                            {sug.text}
                          </span>
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Chat Input Bar */}
      <div className="border-t border-[var(--border)] p-4 bg-[var(--muted)]/10">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSubmit(input);
          }}
          className="flex items-center gap-3 max-w-4xl mx-auto"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={isInitializing ? "Initializing assistant..." : "Type your message to analyze chat dynamics..."}
            className="flex-1 rounded-xl border border-[var(--border)] bg-[var(--card)] px-5 py-3.5 text-sm text-[var(--foreground)] shadow-2xs outline-none focus:border-[var(--primary)] focus:ring-1 focus:ring-[var(--primary)] transition-all duration-200"
            disabled={isInitializing || isLoading}
          />
          <Button
            type="submit"
            className="p-3.5 rounded-xl shrink-0 h-auto cursor-pointer"
            disabled={isInitializing || !input.trim() || isLoading}
          >
            <Send className="h-5 w-5" />
          </Button>
        </form>
      </div>
    </div>
  );
}
