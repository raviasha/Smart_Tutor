"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import VideoInput from "@/components/VideoInput";
import VideoPlayer from "@/components/VideoPlayer";
import TranscriptSidebar from "@/components/TranscriptSidebar";
import QAPanel from "@/components/QAPanel";
import VideoStatusPoller from "@/components/VideoStatusPoller";
import { getTranscript, getVideo, getQAHistory } from "@/lib/api";

interface Video {
  id: string;
  youtube_video_id: string;
  title: string;
  url: string;
  summary: any;
  status: string;
}

interface TranscriptChunk {
  id: string;
  start_time: number;
  end_time: number;
  text: string;
}

interface QAEntry {
  id: string;
  timestamp: number;
  question: string;
  answer: string;
}

export default function LearnPage() {
  const { user, loading, signOut } = useAuth();
  const router = useRouter();

  const [video, setVideo] = useState<Video | null>(null);
  const [transcript, setTranscript] = useState<TranscriptChunk[]>([]);
  const [qaHistory, setQaHistory] = useState<QAEntry[]>([]);
  const [currentTime, setCurrentTime] = useState(0);
  const [pauseTime, setPauseTime] = useState(0);

  // Redirect if not authenticated
  useEffect(() => {
    if (!loading && !user) {
      router.push("/");
    }
  }, [user, loading, router]);

  // Load transcript and Q&A when video is ready
  const loadVideoData = useCallback(async (videoId: string) => {
    try {
      const [transcriptData, videoData, qaData] = await Promise.all([
        getTranscript(videoId),
        getVideo(videoId),
        getQAHistory(videoId),
      ]);

      setTranscript(transcriptData.chunks || []);
      setVideo(videoData);
      setQaHistory(
        (qaData.history || []).map((qa: any) => ({
          id: qa.id,
          timestamp: qa.video_timestamp,
          question: qa.question,
          answer: qa.answer,
        }))
      );
    } catch (err) {
      console.error("Failed to load video data:", err);
    }
  }, []);

  const handleVideoSubmitted = (submittedVideo: Video) => {
    setVideo(submittedVideo);
    setTranscript([]);
    setQaHistory([]);
    setCurrentTime(0);
    setPauseTime(0);

    if (submittedVideo.status === "ready") {
      loadVideoData(submittedVideo.id);
    }
  };

  const handlePause = useCallback((timestamp: number) => {
    setPauseTime(timestamp);
  }, []);

  const handleTimestampChange = useCallback((timestamp: number) => {
    setCurrentTime(timestamp);
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="flex h-screen flex-col bg-gray-50">
      {/* Top Bar */}
      <header className="flex items-center justify-between border-b border-gray-200 bg-white px-6 py-3">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🎓</span>
          <h1 className="text-lg font-bold text-gray-900">Smart Tutor</h1>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-500">{user.email}</span>
          <button
            onClick={() => signOut()}
            className="rounded-lg bg-gray-100 px-3 py-1.5 text-sm text-gray-600 transition hover:bg-gray-200"
          >
            Sign Out
          </button>
        </div>
      </header>

      {/* Video Input Bar */}
      <div className="border-b border-gray-200 bg-white px-6 py-4">
        <VideoInput onVideoSubmitted={handleVideoSubmitted} />
      </div>

      {/* Main Content Area */}
      {video ? (
        <>
          {/* Status Poller (if processing) */}
          {video.status === "processing" && (
            <div className="px-6 pt-4">
              <VideoStatusPoller
                videoId={video.id}
                initialStatus={video.status}
                onReady={() => loadVideoData(video.id)}
                onFailed={() => setVideo({ ...video, status: "failed" })}
              />
            </div>
          )}

          {video.status === "failed" && (
            <div className="px-6 pt-4">
              <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">
                ❌ Failed to process this video. Please try a different one.
              </div>
            </div>
          )}

          {/* Video Title & Summary */}
          {video.summary && (
            <div className="border-b border-gray-200 bg-white px-6 py-3">
              <h2 className="text-base font-semibold text-gray-800">{video.title}</h2>
              <div className="mt-1 flex items-center gap-3 text-xs text-gray-500">
                <span className="rounded-full bg-blue-100 px-2 py-0.5 text-blue-700">
                  {video.summary.level}
                </span>
                <span>{video.summary.topic}</span>
              </div>
            </div>
          )}

          {/* Three-Panel Layout */}
          <div className="flex flex-1 overflow-hidden">
            {/* Left: Video Player */}
            <div className="flex w-1/2 flex-col border-r border-gray-200 bg-white p-4">
              <VideoPlayer
                youtubeVideoId={video.youtube_video_id}
                onTimestampChange={handleTimestampChange}
                onPause={handlePause}
              />

              {/* Transcript below video */}
              <div className="mt-4 flex-1 overflow-hidden rounded-lg border border-gray-200">
                <TranscriptSidebar
                  chunks={transcript}
                  currentTime={currentTime}
                />
              </div>
            </div>

            {/* Right: Q&A Panel */}
            <div className="flex w-1/2 flex-col bg-white">
              <QAPanel
                videoId={video.id}
                currentTimestamp={pauseTime || currentTime}
                initialHistory={qaHistory}
              />
            </div>
          </div>
        </>
      ) : (
        /* Empty State */
        <div className="flex flex-1 flex-col items-center justify-center">
          <div className="text-center">
            <div className="text-6xl">📺</div>
            <h2 className="mt-4 text-xl font-semibold text-gray-700">
              Ready to learn?
            </h2>
            <p className="mt-2 max-w-md text-sm text-gray-500">
              Paste a YouTube URL above to get started. You can pause the video
              at any point and ask the AI tutor to explain what&apos;s being discussed.
            </p>
            <div className="mt-6 flex flex-col items-center gap-2 text-xs text-gray-400">
              <p>✅ Works with any educational YouTube video</p>
              <p>✅ AI understands the context of what you&apos;re watching</p>
              <p>✅ Your Q&amp;A history is saved for each video</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
