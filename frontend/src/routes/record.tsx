import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { Mic, Square, Play, Pause, Trash2, Send, Loader2, CheckCircle2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { AppLayout } from "@/components/AppLayout";
import { useAudioRecorder } from "@/hooks/useAudioRecorder";

export const Route = createFileRoute("/record")({
  head: () => ({
    meta: [
      { title: "New Handover — SBAR Voice" },
      { name: "description", content: "Record a new voice-powered SBAR shift handover." },
    ],
  }),
  component: RecordPage,
});

function formatTime(s: number) {
  const m = Math.floor(s / 60).toString().padStart(2, "0");
  const sec = Math.floor(s % 60).toString().padStart(2, "0");
  return `${m}:${sec}`;
}

function RecordPage() {
  const {
    isRecording,
    recordingTime,
    audioBlob,
    startRecording,
    stopRecording,
    clearAudio,
  } = useAudioRecorder();

  const [isPlaying, setIsPlaying] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const navigate = useNavigate();

  const [playbackTime, setPlaybackTime] = useState(0);

  useEffect(() => {
    if (audioBlob) {
      const url = URL.createObjectURL(audioBlob);
      setAudioUrl(url);
      return () => URL.revokeObjectURL(url);
    } else {
      setAudioUrl(null);
      setPlaybackTime(0);
    }
  }, [audioBlob]);

  const togglePlay = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        audioRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setPlaybackTime(audioRef.current.currentTime);
    }
  };

  const submit = async () => {
    if (!audioBlob) return;
    try {
      setIsSubmitting(true);
      const API_URL = import.meta.env.VITE_API_URL;
      
      const response = await fetch(`${API_URL}/upload-url`);
      if (!response.ok) throw new Error('Failed to get upload URL from server');
      
      const data = await response.json();
      const { upload_url } = data;
      
      const uploadResponse = await fetch(upload_url, {
        method: 'PUT',
        body: audioBlob,
        headers: {
          'Content-Type': 'audio/webm',
        },
      });
      
      if (!uploadResponse.ok) throw new Error('Failed to upload file to S3');
      
      setUploadSuccess(true);
      setTimeout(() => navigate({ to: "/" }), 2000);
      
    } catch (error) {
      console.error('Upload error:', error);
      alert('Failed to upload audio. Check console for details.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const status =
    !audioBlob && !isRecording
      ? "Ready to record"
      : isRecording
        ? "Recording…"
        : isPlaying
          ? "Playing back"
          : isSubmitting
            ? "Processing your handover"
            : uploadSuccess
              ? "Upload successful!"
              : "Recording ready";

  return (
    <AppLayout
      title="New Handover"
      subtitle="Speak naturally in English or Minglish"
      showSearch={false}
    >
      <div className="flex min-h-[68vh] flex-col items-center justify-center">
        {uploadSuccess ? (
          <div className="flex flex-col items-center justify-center animate-fade-in text-center">
             <div className="flex h-20 w-20 items-center justify-center rounded-full bg-accent-soft text-accent mb-6">
                <CheckCircle2 className="h-10 w-10" />
             </div>
             <h2 className="text-2xl font-bold tracking-tight">Handover Sent!</h2>
             <p className="mt-2 text-muted-foreground">Redirecting to dashboard...</p>
          </div>
        ) : (
          <>
            {/* Microphone */}
            <div className="relative flex items-center justify-center">
              {isRecording && (
                <>
                  <span className="absolute h-40 w-40 rounded-full bg-primary/20 animate-pulse-ring" />
                  <span
                    className="absolute h-40 w-40 rounded-full bg-primary/20 animate-pulse-ring"
                    style={{ animationDelay: "0.6s" }}
                  />
                </>
              )}
              <button
                onClick={!audioBlob ? (isRecording ? stopRecording : startRecording) : undefined}
                disabled={isSubmitting || !!audioBlob}
                aria-label={isRecording ? "Stop recording" : "Start recording"}
                className={
                  "relative flex h-40 w-40 items-center justify-center rounded-full text-primary-foreground shadow-elevated transition-all duration-300 " +
                  (isRecording
                    ? "bg-destructive hover:scale-[0.98]"
                    : isSubmitting
                      ? "bg-primary/70"
                      : audioBlob
                        ? "bg-muted text-muted-foreground"
                        : "bg-primary hover:scale-[1.03] active:scale-[0.98]")
                }
              >
                {isSubmitting ? (
                  <Loader2 className="h-14 w-14 animate-spin" strokeWidth={1.75} />
                ) : isRecording ? (
                  <Square className="h-12 w-12 fill-current" strokeWidth={1.75} />
                ) : (
                  <Mic className="h-14 w-14" strokeWidth={1.75} />
                )}
              </button>
            </div>

            {/* Timer + waveform */}
            <div className="mt-10 h-12 flex items-center justify-center">
              {isRecording || isPlaying ? (
                <div className="flex items-end gap-1.5">
                  {Array.from({ length: 28 }).map((_, i) => (
                    <span
                      key={i}
                      className="w-1.5 rounded-full bg-primary/70"
                      style={{
                        height: `${20 + Math.sin(i * 0.9) * 14 + 16}px`,
                        animation: `wave 1.1s ease-in-out ${i * 0.05}s infinite`,
                      }}
                    />
                  ))}
                </div>
              ) : null}
            </div>

            {/* Status / timer text */}
            <div className="mt-6 text-center">
              {isRecording || audioBlob ? (
                <div className="font-mono text-4xl font-semibold tabular-nums tracking-tight">
                  {formatTime(audioBlob ? playbackTime : recordingTime)}
                </div>
              ) : (
                <div className="text-2xl font-semibold tracking-tight">Tap to Record</div>
              )}
              <div className="mt-2 text-sm text-muted-foreground">{status}</div>
            </div>
            
            {audioUrl && (
              <audio 
                ref={audioRef} 
                src={audioUrl} 
                onTimeUpdate={handleTimeUpdate}
                onEnded={() => {
                  setIsPlaying(false);
                  setPlaybackTime(0);
                }}
                className="hidden" 
              />
            )}

            {/* Post-recording controls */}
            {audioBlob && !isSubmitting ? (
              <div className="mt-10 flex items-center gap-3 animate-fade-in">
                <button
                  onClick={clearAudio}
                  className="flex h-12 items-center gap-2 rounded-full border border-border bg-card px-5 text-sm font-semibold text-destructive transition-all hover:-translate-y-0.5 hover:shadow-soft"
                >
                  <Trash2 className="h-4 w-4" />
                  Discard
                </button>
                <button
                  onClick={togglePlay}
                  className="flex h-12 w-12 items-center justify-center rounded-full border border-border bg-card text-foreground transition-all hover:-translate-y-0.5 hover:shadow-soft"
                  aria-label={isPlaying ? "Pause" : "Play"}
                >
                  {isPlaying ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5 pl-0.5" />}
                </button>
                <button
                  onClick={submit}
                  className="flex h-12 items-center gap-2 rounded-full bg-primary px-6 text-sm font-semibold text-primary-foreground shadow-soft transition-all hover:-translate-y-0.5 hover:shadow-elevated"
                >
                  <Send className="h-4 w-4" />
                  Submit
                </button>
              </div>
            ) : null}
          </>
        )}
      </div>
    </AppLayout>
  );
}
