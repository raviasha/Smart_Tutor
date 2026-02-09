MVP — Version 1 (Audio-first Smart Tutor)
(No visual understanding yet — unchanged from before)
Goal
Enable a learner to:
Paste a YouTube URL
Watch the video
Pause at any moment and ask a question
Receive a context-aware explanation grounded in that moment of the video.

1) Video Ingestion (Must-Have)
The system shall:
Accept a YouTube URL
Extract:
Audio track
YouTube captions if available (as a fallback/augment)

2) Audio → Text (Transcription)
The system shall:
Produce a timestamped transcript, segmented into logical chunks.
Store transcript in a searchable database keyed by time.
Example structure:

[00:00–00:30] Instructor explains X  
[00:30–01:00] Instructor explains Y  

3) One-Time Video Summary
For each video, automatically generate and store:
A 1-paragraph concept summary covering:
Main topic
Level (beginner/intermediate/advanced)
Key ideas
This summary becomes part of the persistent context for all future questions.

4) Interactive Player
The UI must support:
Play / Pause
“Ask a question” input that:
Captures the exact timestamp
Captures the user question

5) Smart Context Retrieval
When the user asks at time T, the system must retrieve:
Video summary
Transcript window around T
Default: T − 30 sec to T + 15 sec
This becomes the AI’s grounding context.

6) AI Answering
AI must return:
Clear text explanation
References to “what was being explained at that moment”
Plain, learner-friendly language

7) Growing Memory Layer
Each Q&A is appended to the video record:

[T] USER QUESTION  
[T] AI ANSWER  
This forms an augmented transcript unique to that learner.
