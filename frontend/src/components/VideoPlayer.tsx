"use client";

import { useEffect, useRef, useState, useCallback } from "react";

declare global {
  interface Window {
    YT: any;
    onYouTubeIframeAPIReady: () => void;
  }
}

interface VideoPlayerProps {
  youtubeVideoId: string;
  onTimestampChange?: (timestamp: number) => void;
  onPause?: (timestamp: number) => void;
}

export default function VideoPlayer({
  youtubeVideoId,
  onTimestampChange,
  onPause,
}: VideoPlayerProps) {
  const playerRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);

  const initPlayer = useCallback(() => {
    if (!containerRef.current || !window.YT?.Player) return;

    // Destroy existing player if any
    if (playerRef.current) {
      playerRef.current.destroy();
    }

    playerRef.current = new window.YT.Player(containerRef.current, {
      videoId: youtubeVideoId,
      width: "100%",
      height: "100%",
      playerVars: {
        autoplay: 0,
        modestbranding: 1,
        rel: 0,
      },
      events: {
        onReady: () => setIsReady(true),
        onStateChange: (event: any) => {
          // YT.PlayerState.PAUSED === 2
          if (event.data === 2) {
            const time = playerRef.current.getCurrentTime();
            setCurrentTime(time);
            onPause?.(time);
          }

          // Track time while playing
          if (event.data === 1) {
            // PLAYING
            intervalRef.current = setInterval(() => {
              if (playerRef.current) {
                const time = playerRef.current.getCurrentTime();
                setCurrentTime(time);
                onTimestampChange?.(time);
              }
            }, 1000);
          } else {
            if (intervalRef.current) {
              clearInterval(intervalRef.current);
              intervalRef.current = null;
            }
          }
        },
      },
    });
  }, [youtubeVideoId, onPause, onTimestampChange]);

  useEffect(() => {
    // Load YouTube IFrame API if not already loaded
    if (window.YT?.Player) {
      initPlayer();
      return;
    }

    // Load the API script
    const tag = document.createElement("script");
    tag.src = "https://www.youtube.com/iframe_api";
    const firstScriptTag = document.getElementsByTagName("script")[0];
    firstScriptTag.parentNode?.insertBefore(tag, firstScriptTag);

    window.onYouTubeIframeAPIReady = () => {
      initPlayer();
    };

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (playerRef.current) playerRef.current.destroy();
    };
  }, [initPlayer]);

  // Reinit when video changes
  useEffect(() => {
    if (window.YT?.Player) {
      initPlayer();
    }
  }, [youtubeVideoId, initPlayer]);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  const pauseVideo = () => {
    if (playerRef.current && isReady) {
      playerRef.current.pauseVideo();
    }
  };

  const seekTo = (seconds: number) => {
    if (playerRef.current && isReady) {
      playerRef.current.seekTo(seconds, true);
    }
  };

  return (
    <div className="w-full">
      <div className="relative aspect-video w-full overflow-hidden rounded-xl bg-black shadow-lg">
        <div ref={containerRef} className="h-full w-full" />
      </div>
      <div className="mt-2 flex items-center justify-between text-sm text-gray-500">
        <span>Current: {formatTime(currentTime)}</span>
        <button
          onClick={pauseVideo}
          className="rounded-md bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700 transition hover:bg-gray-200"
        >
          ⏸ Pause to Ask
        </button>
      </div>
    </div>
  );
}

export type { VideoPlayerProps };
