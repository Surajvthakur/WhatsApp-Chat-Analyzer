"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { X, Send, Bot, User, Loader2 } from "lucide-react";

interface AskAIModalProps {
  chatId: string;
  isOpen: boolean;
  onClose: () => void;
}

interface Message {
  role: "user" | "assistant";
  content: string;
}

export function AskAIModal({ chatId, isOpen, onClose }: AskAIModalProps) {
  const [isInitializing, setIsInitializing] = useState(true);
  const [initError, setInitError] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Initialize session when modal opens
  useEffect(() => {
    if (isOpen) {
      const initSession = async () => {
        setIsInitializing(true);
        setInitError("");
        try {
          const res = await fetch(`${baseUrl}/api/v1/ai/${chatId}/init`, {
            method: "POST",
          });
          if (!res.ok) {
            throw new Error("Failed to initialize AI session");
          }
          
          if (messages.length === 0) {
            setMessages([
              {
                role: "assistant",
                content: "Hi! I've read your chat. Ask me anything about it!",
              },
            ]);
          }
        } catch (err: any) {
          setInitError(err.message || "Something went wrong.");
        } finally {
          setIsInitializing(false);
        }
      };

      initSession();
    }
  }, [isOpen, chatId, baseUrl]);

  // Clean up session on close
  const handleClose = async () => {
    onClose();
    try {
      await fetch(`${baseUrl}/api/v1/ai/${chatId}/close`, {
        method: "DELETE",
      });
    } catch (err) {
      console.error("Failed to close AI session", err);
    }
  };

  // Clean up on unmount or browser close
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (isOpen) {
        fetch(`${baseUrl}/api/v1/ai/${chatId}/close`, {
          method: "DELETE",
          keepalive: true,
        });
      }
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, [isOpen, chatId, baseUrl]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setIsLoading(true);

    try {
      const res = await fetch(`${baseUrl}/api/v1/ai/${chatId}/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question: userMessage }),
      });

      if (!res.ok) {
        throw new Error("Failed to get answer");
      }

      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.answer },
      ]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, I couldn't process that request right now.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="flex h-[80vh] w-full max-w-2xl flex-col overflow-hidden rounded-xl bg-background shadow-2xl border border-[var(--border)]">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[var(--border)] p-4 bg-[var(--muted)]/50">
          <div className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold">Ask AI</h2>
          </div>
          <Button variant="ghost" className="p-2" onClick={handleClose}>
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Content */}
        <div className="flex flex-1 flex-col overflow-hidden bg-background">
          {isInitializing ? (
            <div className="flex flex-1 flex-col items-center justify-center text-center p-8">
              <Loader2 className="h-10 w-10 animate-spin text-primary mb-4" />
              <p className="text-lg font-medium">Initializing AI...</p>
              <p className="text-sm text-muted-foreground mt-2 max-w-md">
                We are generating embeddings for your chat history. This may take
                a moment depending on the size of your chat.
              </p>
            </div>
          ) : initError ? (
            <div className="flex flex-1 flex-col items-center justify-center p-8 text-center">
              <p className="text-destructive mb-2 font-medium">Initialization Failed</p>
              <p className="text-sm text-muted-foreground">{initError}</p>
              <Button onClick={() => setIsInitializing(true)} className="mt-4">
                Retry
              </Button>
            </div>
          ) : (
            <>
              {/* Messages Area */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`flex ${
                      msg.role === "user" ? "justify-end" : "justify-start"
                    }`}
                  >
                    <div
                      className={`flex max-w-[80%] items-start gap-3 rounded-2xl px-4 py-3 ${
                        msg.role === "user"
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted text-foreground"
                      }`}
                    >
                      {msg.role === "assistant" && (
                        <Bot className="mt-0.5 h-5 w-5 shrink-0" />
                      )}
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">
                        {msg.content}
                      </p>
                      {msg.role === "user" && (
                        <User className="mt-0.5 h-5 w-5 shrink-0" />
                      )}
                    </div>
                  </div>
                ))}
                {isLoading && (
                  <div className="flex justify-start">
                    <div className="flex items-center gap-3 rounded-2xl bg-muted px-4 py-3 text-foreground">
                      <Bot className="h-5 w-5 shrink-0" />
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span className="text-sm">Thinking...</span>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input Area */}
              <div className="border-t border-[var(--border)] p-4 bg-[var(--muted)]/30">
                <form
                  onSubmit={handleSubmit}
                  className="flex items-center gap-2"
                >
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask about your chat..."
                    className="flex-1 rounded-full border border-[var(--border)] bg-background px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                    disabled={isLoading}
                  />
                  <Button
                    type="submit"
                    className="p-2 rounded-full shrink-0"
                    disabled={!input.trim() || isLoading}
                  >
                    <Send className="h-4 w-4" />
                  </Button>
                </form>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
