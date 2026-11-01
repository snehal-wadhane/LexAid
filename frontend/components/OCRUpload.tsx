"use client";

import { useRef, useState } from "react";
import Tesseract from "tesseract.js";

interface Props {
  onTextExtracted: (text: string) => void;
}

export function OCRUpload({ onTextExtracted }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState<"idle" | "reading" | "done" | "error">("idle");
  const [progress, setProgress] = useState(0);

  const handleFile = async (file: File) => {
    if (!file.type.startsWith("image/")) {
      setStatus("error");
      return;
    }

    setStatus("reading");
    setProgress(0);

    try {
      const result = await Tesseract.recognize(file, "eng+hin", {
        logger: (m) => {
          if (m.status === "recognizing text") {
            setProgress(Math.round((m.progress ?? 0) * 100));
          }
        },
      });

      const text = result.data.text.trim();
      if (text) {
        onTextExtracted(text);
        setStatus("done");
      } else {
        setStatus("error");
      }
    } catch {
      setStatus("error");
    }

    setTimeout(() => setStatus("idle"), 2500);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    e.target.value = "";
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleChange}
      />

      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        disabled={status === "reading"}
        title="Upload image to extract text (OCR)"
        className={`flex-shrink-0 w-11 h-11 rounded-xl flex items-center justify-center transition-colors border ${
          status === "reading"
            ? "bg-blue-50 border-blue-200 cursor-wait"
            : status === "done"
            ? "bg-green-50 border-green-200"
            : status === "error"
            ? "bg-red-50 border-red-200"
            : "bg-gray-50 border-gray-200 hover:bg-gray-100 hover:border-gray-300"
        }`}
      >
        {status === "reading" ? (
          <div className="flex flex-col items-center">
            <svg className="w-4 h-4 text-blue-500 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
            </svg>
            <span className="text-blue-500 text-[9px] font-medium mt-0.5">{progress}%</span>
          </div>
        ) : status === "done" ? (
          <svg className="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        ) : status === "error" ? (
          <svg className="w-4 h-4 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        )}
      </button>
    </>
  );
}
