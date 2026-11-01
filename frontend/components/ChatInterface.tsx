"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { MessageBubble } from "./MessageBubble";
import { TriageWizard } from "./TriageWizard";
import { supabase, type Conversation } from "@/lib/supabase";
import { OCRUpload } from "./OCRUpload";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिन्दी" },
  { code: "mr", label: "मराठी" },
  { code: "ta", label: "தமிழ்" },
  { code: "te", label: "తెలుగు" },
  { code: "bn", label: "বাংলা" },
];

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: string[];
  streaming?: boolean;
}

const WELCOME: Message = {
  role: "assistant",
  content: [
    "Namaste! I'm LexAid — your Indian legal information assistant.",
    "",
    "Ask me anything about your rights under Indian law, or use the Guided Help panel on the left to find answers for your specific situation.",
    "",
    "Examples:",
    "• My employer hasn't paid me in 2 months. What can I do?",
    "• How do I file an RTI application?",
    "• Can my landlord evict me without notice?",
    "",
    "---",
    "*LexAid provides legal information based on publicly available Indian law. This is not legal advice and does not create a lawyer-client relationship.*",
  ].join("\n"),
};

export function ChatInterface() {
  const router = useRouter();

  // Auth state
  const [user, setUser] = useState<any>(null);
  const [authLoading, setAuthLoading] = useState(true);

  // Chat state
  const [messages, setMessages] = useState<Message[]>([WELCOME]);
  const [input, setInput] = useState("");
  const [language, setLanguage] = useState("en");
  const [loading, setLoading] = useState(false);

  // History state
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);

  // ── Auth check ──────────────────────────────────────────────────────────────
  useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (!user) {
        router.push("/auth");
      } else {
        setUser(user);
        loadConversations(user.id);
      }
      setAuthLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event) => {
      if (event === "SIGNED_OUT") router.push("/auth");
    });
    return () => subscription.unsubscribe();
  }, [router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── Load conversation list ──────────────────────────────────────────────────
  const loadConversations = async (userId: string) => {
    const { data } = await supabase
      .from("conversations")
      .select("id, title, created_at")
      .eq("user_id", userId)
      .order("created_at", { ascending: false })
      .limit(30);
    if (data) setConversations(data as Conversation[]);
  };

  // ── Load a past conversation ────────────────────────────────────────────────
  const openConversation = async (convId: string) => {
    const { data } = await supabase
      .from("messages")
      .select("role, content, sources")
      .eq("conversation_id", convId)
      .order("created_at", { ascending: true });

    if (data) {
      const loaded: Message[] = data.map((m: any) => ({
        role: m.role,
        content: m.content,
        sources: m.sources ?? [],
      }));
      setMessages([WELCOME, ...loaded]);
      setActiveConvId(convId);
    }
  };

  // ── Save Q&A pair to Supabase ───────────────────────────────────────────────
  const saveToSupabase = useCallback(
    async (question: string, answer: string, sources: string[], convId: string | null) => {
      if (!user) return convId;

      let cid = convId;
      if (!cid) {
        const title = question.slice(0, 60) + (question.length > 60 ? "…" : "");
        const { data: conv, error } = await supabase
          .from("conversations")
          .insert({ user_id: user.id, title })
          .select("id, title, created_at")
          .single();
        if (error || !conv) return null;
        cid = conv.id;
        setActiveConvId(cid);
        setConversations((prev) => [conv as Conversation, ...prev]);
      }

      await supabase.from("messages").insert([
        { conversation_id: cid, user_id: user.id, role: "user",      content: question, sources: [] },
        { conversation_id: cid, user_id: user.id, role: "assistant", content: answer,   sources },
      ]);

      return cid;
    },
    [user]
  );

  // ── New chat ────────────────────────────────────────────────────────────────
  const startNewChat = () => {
    setMessages([WELCOME]);
    setActiveConvId(null);
    setInput("");
  };

  // ── Logout ──────────────────────────────────────────────────────────────────
  const handleLogout = async () => {
    await supabase.auth.signOut();
  };

  // ── Feedback ─────────────────────────────────────────────────────────────────
  const handleFeedback = async (msgIndex: number, rating: 1 | -1) => {
    if (!user) return;
    const msg = messages[msgIndex];
    const prevMsg = messages[msgIndex - 1];
    await supabase.from("feedback").insert({
      user_id: user.id,
      conversation_id: activeConvId,
      question: prevMsg?.role === "user" ? prevMsg.content : null,
      answer_snippet: msg.content.slice(0, 400),
      rating,
    });
  };

  // ── Send query ──────────────────────────────────────────────────────────────
  const sendQuery = async (question: string, category?: string) => {
    if (!question.trim() || loading) return;

    // Build history: skip welcome (index 0), skip streaming, last 6 messages
    const history = messages
      .slice(1)
      .filter((m) => !m.streaming && m.content.trim())
      .slice(-6)
      .map((m) => ({ role: m.role, content: m.content }));

    const userMsg: Message = { role: "user", content: question.trim() };
    const assistantMsg: Message = { role: "assistant", content: "", streaming: true };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setInput("");
    setLoading(true);

    let fullAnswer = "";
    let finalSources: string[] = [];
    let currentConvId = activeConvId;

    try {
      const res = await fetch(`${API}/api/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: question.trim(), language, category, history }),
      });

      if (!res.ok) throw new Error(`Server error ${res.status}`);

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          if (!part.startsWith("data: ")) continue;
          try {
            const evt = JSON.parse(part.slice(6));
            if (evt.type === "sources") {
              finalSources = evt.sources;
              setMessages((prev) => {
                const copy = [...prev];
                copy[copy.length - 1] = { ...copy[copy.length - 1], sources: finalSources };
                return copy;
              });
            } else if (evt.type === "token") {
              fullAnswer += evt.text;
              setMessages((prev) => {
                const copy = [...prev];
                copy[copy.length - 1] = {
                  ...copy[copy.length - 1],
                  content: copy[copy.length - 1].content + evt.text,
                };
                return copy;
              });
            } else if (evt.type === "done") {
              setMessages((prev) => {
                const copy = [...prev];
                copy[copy.length - 1] = { ...copy[copy.length - 1], streaming: false };
                return copy;
              });
            } else if (evt.type === "error") {
              setMessages((prev) => {
                const copy = [...prev];
                copy[copy.length - 1] = {
                  role: "assistant",
                  content: `Sorry, I encountered an error: ${evt.message}`,
                  streaming: false,
                };
                return copy;
              });
            }
          } catch {
            // skip malformed event
          }
        }
      }

      // Save to Supabase after full answer received
      if (fullAnswer) {
        currentConvId = await saveToSupabase(
          question.trim(),
          fullAnswer,
          finalSources,
          currentConvId
        );
      }
    } catch {
      setMessages((prev) => {
        const copy = [...prev];
        copy[copy.length - 1] = {
          role: "assistant",
          content: "Sorry, I could not connect to the server. Please make sure the backend is running.",
          streaming: false,
        };
        return copy;
      });
    } finally {
      setLoading(false);
      setMessages((prev) => {
        const copy = [...prev];
        if (copy[copy.length - 1].streaming) {
          copy[copy.length - 1] = { ...copy[copy.length - 1], streaming: false };
        }
        return copy;
      });
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendQuery(input);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendQuery(input);
    }
  };

  // ── Loading state ───────────────────────────────────────────────────────────
  if (authLoading) {
    return (
      <div className="min-h-screen bg-[#1B2A4A] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 bg-orange-500 rounded-xl flex items-center justify-center text-white font-bold text-lg">
            L
          </div>
          <p className="text-gray-400 text-sm">Loading…</p>
        </div>
      </div>
    );
  }

  // ── Main UI ─────────────────────────────────────────────────────────────────
  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-72 flex-shrink-0 bg-[#1B2A4A] flex flex-col overflow-hidden">

        {/* Logo */}
        <div className="px-5 py-5 border-b border-white/10">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-orange-500 rounded-lg flex items-center justify-center text-white font-bold text-sm">
              L
            </div>
            <div>
              <h1 className="text-white font-bold text-lg leading-tight">LexAid</h1>
              <p className="text-gray-400 text-xs">Indian Legal Assistant</p>
            </div>
          </div>
        </div>

        {/* New Chat button */}
        <div className="px-4 pt-4 pb-2">
          <button
            onClick={startNewChat}
            className="w-full flex items-center gap-2 px-3 py-2.5 rounded-xl border border-white/20 text-gray-300 hover:bg-white/10 hover:text-white transition-colors text-sm font-medium"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            New Chat
          </button>
        </div>

        {/* Conversation history */}
        <div className="px-4 pb-1">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">History</p>
        </div>
        <div className="px-2 max-h-44 overflow-y-auto flex flex-col gap-0.5 mb-2">
          {conversations.length === 0 ? (
            <p className="text-xs text-gray-600 px-2 py-1">No previous chats yet</p>
          ) : (
            conversations.map((c) => (
              <button
                key={c.id}
                onClick={() => openConversation(c.id)}
                className={`w-full text-left px-3 py-2 rounded-lg text-xs truncate transition-colors ${
                  activeConvId === c.id
                    ? "bg-orange-500/20 text-orange-300"
                    : "text-gray-400 hover:bg-white/10 hover:text-gray-200"
                }`}
              >
                {c.title}
              </button>
            ))
          )}
        </div>

        {/* Divider */}
        <div className="border-t border-white/10 mx-4 mb-3" />

        {/* Triage wizard */}
        <div className="flex-1 overflow-y-auto">
          <div className="px-5 pb-1">
            <p className="text-xs font-semibold text-orange-400 uppercase tracking-wider">
              Guided Help
            </p>
          </div>
          <TriageWizard onQuery={(q, cat) => sendQuery(q, cat)} />
        </div>

        {/* Language selector */}
        <div className="border-t border-white/10 px-5 py-3">
          <p className="text-xs text-gray-400 mb-2">Language</p>
          <div className="grid grid-cols-3 gap-1">
            {LANGUAGES.map((l) => (
              <button
                key={l.code}
                onClick={() => setLanguage(l.code)}
                className={`text-xs rounded px-1.5 py-1 transition-all ${
                  language === l.code
                    ? "bg-orange-500 text-white font-semibold"
                    : "text-gray-400 hover:text-gray-200 hover:bg-white/10"
                }`}
              >
                {l.label}
              </button>
            ))}
          </div>
        </div>

        {/* User + Logout */}
        <div className="border-t border-white/10 px-4 py-3 flex items-center justify-between gap-2">
          <p className="text-xs text-gray-400 truncate">{user?.email}</p>
          <button
            onClick={handleLogout}
            className="text-xs text-gray-500 hover:text-red-400 transition-colors flex-shrink-0"
            title="Sign out"
          >
            Sign out
          </button>
        </div>
      </aside>

      {/* Main chat area */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="flex-shrink-0 bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
          <div>
            <h2 className="font-semibold text-gray-800 text-sm">Legal Q&amp;A</h2>
            <p className="text-xs text-gray-400">Ask about your rights under Indian law</p>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-green-500 rounded-full" />
            <span className="text-xs text-gray-500">Connected</span>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {messages.map((msg, i) => (
            <MessageBubble
              key={i}
              msg={msg}
              msgIndex={i}
              onFeedback={msg.role === "assistant" ? handleFeedback : undefined}
            />
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="flex-shrink-0 border-t border-gray-200 bg-white px-6 py-4">
          <form onSubmit={handleSubmit} className="flex gap-3 items-end">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              placeholder="Ask about your legal rights… or upload a document image 📷"
              rows={2}
              className="flex-1 resize-none border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-orange-400 focus:border-transparent disabled:opacity-50 bg-gray-50"
            />
            <OCRUpload onTextExtracted={(text) => setInput((prev) => prev ? prev + "\n\n" + text : text)} />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="flex-shrink-0 w-11 h-11 bg-orange-500 hover:bg-orange-600 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl flex items-center justify-center transition-colors shadow-sm"
            >
              {loading ? (
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              )}
            </button>
          </form>
          <p className="text-xs text-gray-400 mt-2 text-center">
            LexAid provides legal information only — not legal advice
          </p>
        </div>
      </main>
    </div>
  );
}
