"use client";

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { askQuestionStream } from "@/lib/api";

interface QAEntry {
  id?: string;
  timestamp: number;
  question: string;
  answer: string;
  isStreaming?: boolean;
}

interface QAPanelProps {
  videoId: string;
  currentTimestamp: number;
  initialHistory?: QAEntry[];
}

export default function QAPanel({
  videoId,
  currentTimestamp,
  initialHistory = [],
}: QAPanelProps) {
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<QAEntry[]>(initialHistory);
  const [isAsking, setIsAsking] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Scroll to bottom when new Q&A appears
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || isAsking) return;

    const userQuestion = question.trim();
    setQuestion("");
    setError("");
    setIsAsking(true);

    // Add question to history with empty answer (will stream in)
    const newEntry: QAEntry = {
      timestamp: currentTimestamp,
      question: userQuestion,
      answer: "",
      isStreaming: true,
    };

    setHistory((prev) => [...prev, newEntry]);
    const entryIndex = history.length;

    try {
      await askQuestionStream(
        videoId,
        currentTimestamp,
        userQuestion,
        // onChunk: append text as it streams in
        (text: string) => {
          setHistory((prev) => {
            const updated = [...prev];
            updated[entryIndex] = {
              ...updated[entryIndex],
              answer: updated[entryIndex].answer + text,
            };
            return updated;
          });
        },
        // onDone: mark as complete
        (qaId: string) => {
          setHistory((prev) => {
            const updated = [...prev];
            updated[entryIndex] = {
              ...updated[entryIndex],
              id: qaId,
              isStreaming: false,
            };
            return updated;
          });
          setIsAsking(false);
        }
      );
    } catch (err: any) {
      setError(err.message || "Failed to get answer");
      // Remove the failed entry
      setHistory((prev) => prev.slice(0, -1));
      setIsAsking(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-gray-200 px-4 py-3">
        <h3 className="text-sm font-semibold text-gray-700">💬 Ask a Question</h3>
        <p className="text-xs text-gray-400">
          Pause the video and ask about what you&apos;re learning
        </p>
      </div>

      {/* Q&A History */}
      <div className="flex-1 overflow-y-auto p-4">
        {history.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="text-4xl">🤔</div>
            <p className="mt-3 text-sm text-gray-400">
              No questions yet. Pause the video and ask anything!
            </p>
            <p className="mt-1 text-xs text-gray-300">
              The AI will use the video transcript to answer.
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {history.map((entry, i) => (
              <div key={i} className="space-y-3">
                {/* Question */}
                <div className="flex items-start gap-2">
                  <div className="mt-0.5 rounded-full bg-blue-100 p-1.5 text-xs">👤</div>
                  <div className="flex-1">
                    <div className="flex items-baseline gap-2">
                      <span className="text-xs font-medium text-blue-600">
                        at {formatTime(entry.timestamp)}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-gray-800">{entry.question}</p>
                  </div>
                </div>

                {/* Answer */}
                <div className="flex items-start gap-2">
                  <div className="mt-0.5 rounded-full bg-green-100 p-1.5 text-xs">🤖</div>
                  <div className="flex-1 rounded-lg bg-gray-50 p-3">
                    {entry.answer ? (
                      <div className="prose prose-sm max-w-none text-gray-700">
                        <ReactMarkdown>{entry.answer}</ReactMarkdown>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 text-sm text-gray-400">
                        <svg
                          className="h-4 w-4 animate-spin"
                          fill="none"
                          viewBox="0 0 24 24"
                        >
                          <circle
                            className="opacity-25"
                            cx="12"
                            cy="12"
                            r="10"
                            stroke="currentColor"
                            strokeWidth="4"
                          />
                          <path
                            className="opacity-75"
                            fill="currentColor"
                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                          />
                        </svg>
                        Thinking...
                      </div>
                    )}
                    {entry.isStreaming && entry.answer && (
                      <span className="inline-block h-4 w-1 animate-pulse bg-blue-500" />
                    )}
                  </div>
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 p-4">
        {error && (
          <div className="mb-2 rounded-lg bg-red-50 p-2 text-xs text-red-600">
            {error}
          </div>
        )}
        <form onSubmit={handleAsk} className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={
              isAsking
                ? "Waiting for answer..."
                : `Ask about what's happening at ${formatTime(currentTimestamp)}...`
            }
            disabled={isAsking}
            className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50"
          />
          <button
            type="submit"
            disabled={isAsking || !question.trim()}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Ask
          </button>
        </form>
      </div>
    </div>
  );
}
