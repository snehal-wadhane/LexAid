"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Source {
  act: string;
  score: number;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: string[];
  chunks?: Source[];
  streaming?: boolean;
}

interface Props {
  msg: Message;
  msgIndex?: number;
  onFeedback?: (index: number, rating: 1 | -1) => void;
}

export function MessageBubble({ msg, msgIndex, onFeedback }: Props) {
  const [rating, setRating] = useState<1 | -1 | null>(null);

  if (msg.role === "user") {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-[75%] bg-orange-500 text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-sm">
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
        </div>
      </div>
    );
  }

  const handleFeedback = (value: 1 | -1) => {
    if (rating !== null || !onFeedback || msgIndex === undefined) return;
    setRating(value);
    onFeedback(msgIndex, value);
  };

  return (
    <div className="flex justify-start mb-4">
      <div className="max-w-[85%]">
        {/* Sources shown above answer */}
        {msg.sources && msg.sources.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-2">
            {msg.sources.map((s) => (
              <span
                key={s}
                className="text-xs bg-blue-100 text-blue-800 border border-blue-200 rounded-full px-2 py-0.5 font-medium"
              >
                📜 {s}
              </span>
            ))}
          </div>
        )}

        <div className="bg-white rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm border border-gray-100">
          {msg.streaming && msg.content === "" ? (
            <div className="flex items-center gap-1.5 py-1">
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
            </div>
          ) : (
            <div className="text-sm leading-relaxed text-gray-800 prose prose-sm max-w-none
              prose-headings:font-semibold prose-headings:text-gray-900
              prose-strong:font-semibold prose-strong:text-gray-900
              prose-p:my-1 prose-ul:my-1 prose-ol:my-1
              prose-li:my-0.5 prose-hr:my-3 prose-hr:border-gray-200
              prose-code:bg-gray-100 prose-code:px-1 prose-code:rounded prose-code:text-xs
              prose-table:w-full prose-table:text-sm prose-th:bg-orange-50 prose-th:text-gray-800
              prose-td:border prose-td:border-gray-200 prose-th:border prose-th:border-gray-300
              prose-tr:even:bg-gray-50">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
              {msg.streaming && (
                <span className="inline-block w-0.5 h-4 bg-orange-500 ml-0.5 animate-pulse align-middle" />
              )}
            </div>
          )}
        </div>

        {/* Feedback buttons — only after streaming completes */}
        {!msg.streaming && msg.content && onFeedback && msgIndex !== undefined && (
          <div className="flex items-center gap-1.5 mt-1.5 px-1">
            <span className="text-xs text-gray-400 mr-0.5">Helpful?</span>
            <button
              onClick={() => handleFeedback(1)}
              title="Helpful"
              className={`w-7 h-7 rounded-lg flex items-center justify-center text-sm transition-all ${
                rating === 1
                  ? "bg-green-100 text-green-600"
                  : rating !== null
                  ? "opacity-30 cursor-default"
                  : "hover:bg-gray-100 text-gray-400 hover:text-green-600"
              }`}
            >
              👍
            </button>
            <button
              onClick={() => handleFeedback(-1)}
              title="Not helpful"
              className={`w-7 h-7 rounded-lg flex items-center justify-center text-sm transition-all ${
                rating === -1
                  ? "bg-red-100 text-red-500"
                  : rating !== null
                  ? "opacity-30 cursor-default"
                  : "hover:bg-gray-100 text-gray-400 hover:text-red-500"
              }`}
            >
              👎
            </button>
            {rating !== null && (
              <span className="text-xs text-gray-400 ml-1">
                {rating === 1 ? "Thanks!" : "Got it, we'll improve."}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
