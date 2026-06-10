"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { 
  getChatHistory, 
  addChatMessage, 
  ChatMessage,
  saveWorkspace 
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
  Info,
  Save,
  LogIn
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { useWorkspaceStore } from "@/lib/workspace-store";

export default function ChatPage() {
  const { chatId } = useWorkspaceStore();
  const { user, isLoading: authLoading } = useAuth();
  const [workspaceState, setWorkspaceState] = useState<"checking" | "saved" | "unsaved" | "unauthorized">("checking");
  const [isInitializing, setIsInitializing] = useState(true);
  const [loadingStep, setLoadingStep] = useState<"checking" | "loading" | "generating" | "ready">("checking");
  const [initError, setInitError] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSavedWorkspace, setIsSavedWorkspace] = useState(false);
  
  // Workspace saving state (used if workspaceState === "unsaved")
  const [workspaceName, setWorkspaceName] = useState("WhatsApp Chat Analysis");
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

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

  // 1. Verify if workspace is saved in the database
  useEffect(() => {
    let active = true;
    if (authLoading) return;

    if (!user) {
      setWorkspaceState("unauthorized");
      return;
    }

    const checkWorkspaceStatus = async () => {
      try {
        const res = await fetch(`/api/workspaces/${chatId}`, {
          headers: getAuthHeaders(),
        });
        if (res.ok) {
          const data = await res.json();
          if (active) {
            if (data.saved) {
              setWorkspaceState("saved");
            } else {
              setWorkspaceState("unsaved");
            }
          }
        } else {
          if (active) setWorkspaceState("unsaved");
        }
      } catch (err) {
        console.error("Failed to check workspace saved status", err);
        if (active) setWorkspaceState("unsaved");
      }
    };

    checkWorkspaceStatus();

    return () => {
      active = false;
    };
  }, [chatId, user, authLoading]);

  // 2. Initialize session ONLY when workspace is confirmed to be saved
  useEffect(() => {
    if (workspaceState !== "saved") return;

    let active = true;
    const initSession = async () => {
      setIsInitializing(true);
      setInitError("");
      setLoadingStep("checking");
      try {
        // Step 1: Check if embeddings exist in database (Qdrant)
        let hasEmbeddings = false;
        try {
          const statusRes = await fetch(`${baseUrl}/api/v1/ai/${chatId}/status`, {
            headers: getAuthHeaders(),
          });
          if (statusRes.ok) {
            const statusData = await statusRes.json();
            hasEmbeddings = !!statusData.exists;
          }
        } catch (statusErr) {
          console.warn("Failed to check embedding status, defaulting to generate", statusErr);
        }

        if (active) {
          if (hasEmbeddings) {
            setLoadingStep("loading");
          } else {
            setLoadingStep("generating");
          }
        }

        // Step 2: Initialize FastAPI RAM session & generate/load embeddings
        const res = await fetch(`${baseUrl}/api/v1/ai/${chatId}/init`, {
          method: "POST",
          headers: getAuthHeaders(),
        });
        if (!res.ok) {
          let errMsg = "Failed to initialize AI session";
          try {
            const errData = await res.json();
            if (errData && errData.detail) {
              errMsg = errData.detail;
            }
          } catch (e) {
            // ignore JSON parse errors
          }
          throw new Error(errMsg);
        }
        
        // 3. Fetch persistent message history from database
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
        if (active) {
          setLoadingStep("ready");
        }
      } catch (err: any) {
        if (active) {
          const errMsg = err.message || "Something went wrong.";
          setInitError(errMsg);
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
    };
  }, [chatId, baseUrl, workspaceState]);



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

  if (authLoading || workspaceState === "checking") {
    return (
      <div className="flex h-[calc(100vh-8rem)] flex-col items-center justify-center text-center p-8 bg-[var(--card)] rounded-2xl border border-[var(--border)] shadow-md animate-in fade-in duration-200">
        <Loader2 className="h-10 w-10 animate-spin text-[var(--primary)] mb-4" />
        <p className="text-lg font-bold text-[var(--foreground)]">Verifying Workspace Status...</p>
        <p className="text-sm text-[var(--muted-foreground)] mt-2">Please wait while we verify if your workspace is saved.</p>
      </div>
    );
  }

  if (workspaceState === "unauthorized") {
    return (
      <div className="flex h-[calc(100vh-8rem)] flex-col items-center justify-center text-center p-8 bg-[var(--card)] rounded-2xl border border-[var(--border)] shadow-md animate-in fade-in duration-200">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-red-500/10 text-red-500 mb-4">
          <LogIn className="h-6 w-6" />
        </div>
        <h2 className="text-xl font-bold text-[var(--foreground)]">Authentication Required</h2>
        <p className="text-sm text-[var(--muted-foreground)] mt-2 max-w-md">
          You must be logged in to save your workspace and access the Ask AI Chat Assistant.
        </p>
        <Button 
          onClick={() => window.location.href = `/login?callbackUrl=/dashboard/${chatId}/chat`}
          className="mt-6 flex items-center gap-2 rounded-xl"
        >
          <LogIn className="h-4 w-4" />
          Log In / Sign Up
        </Button>
      </div>
    );
  }

  if (workspaceState === "unsaved") {
    return (
      <div className="flex h-[calc(100vh-8rem)] flex-col items-center justify-center p-6 bg-[var(--card)] rounded-2xl border border-[var(--border)] shadow-md animate-in fade-in duration-200">
        <div className="w-full max-w-md overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--card)] p-8 shadow-xl">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[var(--primary)]/10 text-[var(--primary)] mb-4">
            <Save className="h-6 w-6" />
          </div>
          <h3 className="text-xl font-bold text-[var(--foreground)]">Save Workspace</h3>
          <p className="mt-2 text-sm text-[var(--muted-foreground)] leading-relaxed">
            Before you can ask AI questions about this WhatsApp chat, you must first save it to your account. This compiles statistics and sets up the vector search database.
          </p>
          
          <div className="mt-6">
            <label htmlFor="workspace-name-input" className="block text-xs font-semibold text-[var(--muted-foreground)] uppercase tracking-wider mb-2">
              Workspace Name
            </label>
            <input
              id="workspace-name-input"
              type="text"
              value={workspaceName}
              onChange={(e) => setWorkspaceName(e.target.value)}
              className="w-full rounded-xl border border-[var(--border)] bg-transparent px-4 py-3 text-sm text-[var(--foreground)] outline-none focus:border-[var(--primary)] focus:ring-1 focus:ring-[var(--primary)] transition-all"
              placeholder="e.g. Chat with Friends"
              disabled={isSaving || saveSuccess}
            />
          </div>
           
          {saveError && (
            <p className="mt-3 text-sm text-red-500 font-medium">
              {saveError}
            </p>
          )}
          
          {saveSuccess && (
            <p className="mt-3 text-sm text-[var(--primary)] font-medium flex items-center gap-1.5">
              <span>✓ Workspace saved successfully! Initializing AI session...</span>
            </p>
          )}
          
          <div className="mt-8 flex justify-end gap-3">
            <Button
              variant="outline"
               onClick={() => {
                 window.location.href = `/dashboard/${chatId}`;
               }}
              disabled={isSaving || saveSuccess}
              className="rounded-xl px-5"
            >
              Go Back
            </Button>
            <Button
              onClick={async () => {
                if (!workspaceName.trim()) {
                  setSaveError("Workspace name cannot be empty.");
                  return;
                }
                setIsSaving(true);
                setSaveError(null);
                try {
                  const response = await saveWorkspace(chatId, workspaceName);
                  setSaveSuccess(true);
                  setTimeout(() => {
                    window.location.href = `/dashboard/${response.workspace.id}/chat`;
                  }, 1500);
                } catch (err: any) {
                  setSaveError(err.message || "Failed to save workspace.");
                } finally {
                  setIsSaving(false);
                }
              }}
              disabled={isSaving || saveSuccess}
              className="flex items-center gap-2 rounded-xl px-5"
            >
              {isSaving ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Saving…
                </>
              ) : (
                <>
                  <Save className="h-4 w-4" />
                  Save & Continue
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    );
  }

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
            <p className="text-lg font-bold text-[var(--foreground)]">
              {loadingStep === "checking" && "Checking database for existing embeddings..."}
              {loadingStep === "loading" && "Loading embeddings from database..."}
              {loadingStep === "generating" && "Generating AI embeddings..."}
            </p>
            <p className="text-sm text-[var(--muted-foreground)] mt-2 max-w-md leading-relaxed">
              {loadingStep === "checking" && "We are checking Qdrant for previously indexed vectors of this chat..."}
              {loadingStep === "loading" && "Embeddings already exist! Fast-loading conversation vectors..."}
              {loadingStep === "generating" && "Embeddings are not present in database. Processing chat data and generating new vectors using Gemini API (this may take a few moments)..."}
            </p>
          </div>
        ) : initError ? (
          <div className="flex h-full flex-col items-center justify-center p-8 text-center max-w-lg mx-auto">
            {initError.toLowerCase().includes("rate limit") || 
             initError.toLowerCase().includes("quota") || 
             initError.toLowerCase().includes("429") || 
             initError.toLowerCase().includes("resource_exhausted") ? (
              <div className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-8 shadow-xs flex flex-col items-center text-center backdrop-blur-xs">
                <div className="flex h-14 w-14 items-center justify-center rounded-full bg-amber-500/20 text-amber-500 mb-6 animate-pulse">
                  <Clock className="h-7 w-7" />
                </div>
                <h3 className="text-xl font-bold text-amber-500 mb-3">Rate Limit Exceeded</h3>
                <p className="text-sm text-[var(--foreground)] font-medium mb-4 max-w-sm">
                  {initError}
                </p>
                <div className="text-xs text-[var(--muted-foreground)] leading-relaxed bg-[var(--muted)]/50 border border-[var(--border)]/30 rounded-xl p-4 mb-6 text-left">
                  <span className="font-semibold text-[var(--foreground)] block mb-1">Why am I seeing this?</span>
                  Gemini free-tier API keys are subject to strict rate limits (typically 15 requests per minute). Processing large WhatsApp exports requires multiple embedding API requests in quick succession, which can trigger this limit.
                </div>
                <div className="flex flex-col gap-3 w-full">
                  <Button onClick={() => window.location.reload()} className="w-full bg-amber-500 hover:bg-amber-600 text-white font-semibold">
                    Retry Connection
                  </Button>
                </div>
              </div>
            ) : (
              <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-8 shadow-xs flex flex-col items-center text-center max-w-md backdrop-blur-xs">
                <div className="flex h-14 w-14 items-center justify-center rounded-full bg-red-500/20 text-red-500 mb-6">
                  <Info className="h-7 w-7" />
                </div>
                <h3 className="text-xl font-bold text-red-500 mb-3">Initialization Failed</h3>
                <p className="text-sm text-[var(--muted-foreground)] mb-6 max-w-sm">
                  {initError}
                </p>
                <Button onClick={() => window.location.reload()} className="w-full font-semibold">
                  Retry Connection
                </Button>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-6">


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
