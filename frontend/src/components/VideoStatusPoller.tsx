"use client";

import { useEffect, useState } from "react";
import { getVideoStatus } from "@/lib/api";

interface VideoStatusPollerProps {
  videoId: string;
  initialStatus: string;
  onReady: () => void;
  onFailed: () => void;
}

export default function VideoStatusPoller({
  videoId,
  initialStatus,
  onReady,
  onFailed,
}: VideoStatusPollerProps) {
  const [status, setStatus] = useState(initialStatus);

  useEffect(() => {
    if (status === "ready" || status === "failed") return;

    const interval = setInterval(async () => {
      try {
        const data = await getVideoStatus(videoId);
        setStatus(data.status);
        if (data.status === "ready") {
          onReady();
          clearInterval(interval);
        } else if (data.status === "failed") {
          onFailed();
          clearInterval(interval);
        }
      } catch {
        // Silently retry
      }
    }, 3000); // Poll every 3 seconds

    return () => clearInterval(interval);
  }, [videoId, status, onReady, onFailed]);

  if (status === "ready") return null;

  if (status === "failed") {
    return (
      <div className="flex items-center gap-2 rounded-lg bg-red-50 p-4 text-sm text-red-700">
        <span>❌</span>
        <span>Failed to process this video. Please try a different one.</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3 rounded-lg bg-yellow-50 p-4 text-sm text-yellow-800">
      <svg className="h-5 w-5 animate-spin text-yellow-600" fill="none" viewBox="0 0 24 24">
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
      <div>
        <p className="font-medium">Processing video...</p>
        <p className="text-xs text-yellow-600">
          Extracting transcript and generating summary. This usually takes 30–60 seconds.
        </p>
      </div>
    </div>
  );
}
