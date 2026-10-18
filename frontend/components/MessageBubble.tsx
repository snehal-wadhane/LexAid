"use client";

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

export function MessageBubble({ msg }: { msg: Message }) {
  if (msg.role === "user") {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-[75%] bg-orange-500 text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-sm">
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
        </div>
      </div>
    );
  }

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
      </div>
    </div>
  );
}
