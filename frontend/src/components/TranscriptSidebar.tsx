"use client";

import { useEffect, useRef, useState } from "react";

interface TranscriptChunk {
  id: string;
  start_time: number;
  end_time: number;
  text: string;
}

interface TranscriptSidebarProps {
  chunks: TranscriptChunk[];
  currentTime: number;
  onSeek?: (time: number) => void;
}

export default function TranscriptSidebar({
  chunks,
  currentTime,
  onSeek,
}: TranscriptSidebarProps) {
  const activeRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // Auto-scroll to active chunk
  useEffect(() => {
    if (autoScroll && activeRef.current) {
      activeRef.current.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    }
  }, [currentTime, autoScroll]);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  const isActive = (chunk: TranscriptChunk) =>
    currentTime >= chunk.start_time && currentTime < chunk.end_time;

  if (chunks.length === 0) {
    return (
      <div className="flex h-full items-center justify-center p-4 text-sm text-gray-400">
        Transcript will appear here once the video is processed.
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
        <h3 className="text-sm font-semibold text-gray-700">📜 Transcript</h3>
        <button
          onClick={() => setAutoScroll(!autoScroll)}
          className={`rounded px-2 py-1 text-xs transition ${
            autoScroll
              ? "bg-blue-100 text-blue-700"
              : "bg-gray-100 text-gray-500"
          }`}
        >
          {autoScroll ? "Auto-scroll ON" : "Auto-scroll OFF"}
        </button>
      </div>
      <div
        className="flex-1 overflow-y-auto p-4"
        onMouseEnter={() => setAutoScroll(false)}
        onMouseLeave={() => setAutoScroll(true)}
      >
        <div className="space-y-2">
          {chunks.map((chunk) => {
            const active = isActive(chunk);
            return (
              <div
                key={chunk.id}
                ref={active ? activeRef : null}
                onClick={() => onSeek?.(chunk.start_time)}
                className={`cursor-pointer rounded-lg p-3 text-sm transition ${
                  active
                    ? "bg-blue-50 text-blue-900 ring-1 ring-blue-200"
                    : "text-gray-600 hover:bg-gray-50"
                }`}
              >
                <span
                  className={`mr-2 font-mono text-xs ${
                    active ? "text-blue-500" : "text-gray-400"
                  }`}
                >
                  {formatTime(chunk.start_time)}
                </span>
                {chunk.text}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
