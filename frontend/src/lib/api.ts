const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

async function getAuthHeaders(): Promise<HeadersInit> {
  const { createClient } = await import("./supabase");
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session?.access_token) {
    throw new Error("Not authenticated");
  }

  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${session.access_token}`,
  };
}

// ---- Video APIs ----

export async function submitVideo(url: string) {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/videos/`, {
    method: "POST",
    headers,
    body: JSON.stringify({ url }),
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to submit video");
  }
  return res.json();
}

export async function getVideoStatus(videoId: string) {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/videos/${videoId}/status`, { headers });

  if (!res.ok) throw new Error("Failed to get video status");
  return res.json();
}

export async function getVideo(videoId: string) {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/videos/${videoId}`, { headers });

  if (!res.ok) throw new Error("Failed to get video");
  return res.json();
}

// ---- Transcript APIs ----

export async function getTranscript(videoId: string) {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/transcripts/${videoId}`, { headers });

  if (!res.ok) throw new Error("Failed to get transcript");
  return res.json();
}

// ---- Q&A APIs ----

export async function askQuestion(
  videoId: string,
  timestamp: number,
  question: string
) {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/qa/ask`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      video_id: videoId,
      timestamp,
      question,
    }),
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to ask question");
  }
  return res.json();
}

export async function askQuestionStream(
  videoId: string,
  timestamp: number,
  question: string,
  onChunk: (text: string) => void,
  onDone: (qaId: string) => void
) {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/qa/ask/stream`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      video_id: videoId,
      timestamp,
      question,
    }),
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to ask question");
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const data = JSON.parse(line.slice(6));
          if (data.done) {
            onDone(data.qa_id);
          } else if (data.text) {
            onChunk(data.text);
          }
        } catch {
          // skip malformed JSON
        }
      }
    }
  }
}

export async function getQAHistory(videoId: string) {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/qa/history/${videoId}`, { headers });

  if (!res.ok) throw new Error("Failed to get Q&A history");
  return res.json();
}
