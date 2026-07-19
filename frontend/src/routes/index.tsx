import { createFileRoute, Link } from "@tanstack/react-router";
import {
  FileText,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Mic,
  TrendingUp,
  ArrowUpRight,
} from "lucide-react";
import { AppLayout } from "@/components/AppLayout";

export const Route = createFileRoute("/")({
  component: Dashboard,
});

const stats = [
  {
    label: "Total Handovers",
    hint: "Current shift",
    value: "1",
    icon: FileText,
    tone: "primary" as const,
    delta: "+12%",
  },
  {
    label: "Completed",
    hint: "Successfully processed",
    value: "1",
    icon: CheckCircle2,
    tone: "accent" as const,
    delta: "100%",
  },
  {
    label: "Processing",
    hint: "In pipeline",
    value: "0",
    icon: Clock,
    tone: "warning" as const,
    delta: "—",
  },
  {
    label: "Failed",
    hint: "Needs attention",
    value: "0",
    icon: AlertTriangle,
    tone: "destructive" as const,
    delta: "—",
  },
];

const toneMap = {
  primary: "bg-primary-soft text-primary",
  accent: "bg-accent-soft text-accent",
  warning: "bg-warning-soft text-warning-foreground",
  destructive: "bg-destructive-soft text-destructive",
} as const;

const handovers = [
  {
    id: "patient-7",
    patient: "Patient number 7",
    bed: "Bed 3",
    time: "Just now",
    status: "Complete" as const,
    situation: "Patient number 7 in bed number 3 has very high blood pressure.",
    background:
      "The patient has a history of high blood pressure. Their blood pressure was 41.80, which was the same as the last time.",
    assessment:
      "The patient's blood pressure is critically high, and they have a history of hypertension.",
    recommendation: "Refer the patient to the cardiology center.",
  },
];

import { useState, useEffect } from "react";

function Dashboard() {
  const [handovers, setHandovers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    const fetchHandovers = async () => {
      try {
        const apiUrl = import.meta.env.VITE_API_URL;
        if (!apiUrl) {
          throw new Error("VITE_API_URL is undefined in .env");
        }
        
        const response = await fetch(`${apiUrl}/handovers`);
        if (response.ok) {
          const data = await response.json();
          setHandovers(data.handovers || []);
        } else {
          throw new Error(`API returned status ${response.status}`);
        }
      } catch (err: any) {
        console.error("Failed to fetch handovers:", err);
        setErrorMsg(err.message || "Unknown error occurred");
      } finally {
        setLoading(false);
      }
    };
    fetchHandovers();
  }, []);

  const completedCount = handovers.filter(h => h.status?.toUpperCase() === 'COMPLETE').length;
  const processingCount = handovers.filter(h => h.status?.toUpperCase() === 'PROCESSING').length;
  const failedCount = handovers.filter(h => h.status?.toUpperCase() === 'FAILED').length;

  const dynamicStats = [
    {
      label: "Total Handovers",
      hint: "Current shift",
      value: handovers.length.toString(),
      icon: FileText,
      tone: "primary" as const,
      delta: "+12%",
    },
    {
      label: "Completed",
      hint: "Successfully processed",
      value: completedCount.toString(),
      icon: CheckCircle2,
      tone: "accent" as const,
      delta: "100%",
    },
    {
      label: "Processing",
      hint: "In pipeline",
      value: processingCount.toString(),
      icon: Clock,
      tone: "warning" as const,
      delta: "—",
    },
    {
      label: "Failed",
      hint: "Needs attention",
      value: failedCount.toString(),
      icon: AlertTriangle,
      tone: "destructive" as const,
      delta: "—",
    },
  ];

  function getTimeAgo(seconds: number): string {
    if (!seconds) return 'Just now';
    const jsDate = new Date(seconds * 1000);
    const secs = Math.floor((Date.now() - jsDate.getTime()) / 1000);
    if (secs < 60) return 'Just now';
    const mins = Math.floor(secs / 60);
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  }

  return (
    <AppLayout title="Dashboard" subtitle="Shift handover overview">
      {/* Stats grid */}
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {dynamicStats.map((s) => {
          const Icon = s.icon;
          return (
            <div
              key={s.label}
              className="card-hover rounded-3xl border border-border/60 bg-card p-6 shadow-soft"
            >
              <div className="flex items-start justify-between">
                <div className={`flex h-11 w-11 items-center justify-center rounded-2xl ${toneMap[s.tone]}`}>
                  <Icon className="h-5 w-5" strokeWidth={2} />
                </div>
                <span className="inline-flex items-center gap-1 rounded-full bg-accent-soft px-2.5 py-1 text-[11px] font-semibold text-accent">
                  <TrendingUp className="h-3 w-3" />
                  {s.delta}
                </span>
              </div>
              <div className="mt-6 text-4xl font-bold tracking-tight">{loading ? "..." : s.value}</div>
              <div className="mt-1 text-sm font-medium">{s.label}</div>
              <div className="mt-0.5 text-xs text-muted-foreground">{s.hint}</div>
            </div>
          );
        })}
      </section>

      {/* Recent handovers */}
      <section className="mt-10">
        <div className="flex items-end justify-between">
          <div>
            <h2 className="text-xl font-semibold tracking-tight">Recent Handovers</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Latest SBAR reports from the current shift
            </p>
          </div>
          <Link
            to="/record"
            className="inline-flex items-center gap-2 rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow-soft transition-all hover:-translate-y-0.5 hover:shadow-elevated"
          >
            <Mic className="h-4 w-4" />
            New Handover
          </Link>
        </div>

        <div className="mt-5 space-y-4">
          {errorMsg && (
            <div className="rounded-xl bg-destructive-soft p-4 text-destructive border border-destructive/20 mb-4">
              <h3 className="font-semibold">Error Loading Data</h3>
              <p className="text-sm mt-1">{errorMsg}</p>
            </div>
          )}
          {loading && <div className="text-muted-foreground py-10">Loading handovers from AWS...</div>}
          {!loading && !errorMsg && handovers.length === 0 && (
            <div className="text-muted-foreground py-10">No handovers found.</div>
          )}
          {handovers.map((h) => {
            const patientIdStr = typeof h.patient_id === 'string' ? h.patient_id : '';
            const patientNum = patientIdStr.match(/\d+/)?.[0] || '?';
            return (
              <article
                key={h.handover_id || Math.random().toString()}
                className="card-hover rounded-3xl border border-border/60 bg-card p-6 shadow-soft"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary-soft text-sm font-semibold text-primary">
                      P{patientNum}
                    </div>
                    <div>
                      <div className="text-sm font-semibold">{h.patient_id || 'Unknown Patient'}</div>
                      <div className="text-xs text-muted-foreground">Bed 3</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${
                      h.status?.toUpperCase() === 'FAILED' ? 'bg-destructive-soft text-destructive' :
                      h.status?.toUpperCase() === 'COMPLETE' ? 'bg-accent-soft text-accent' :
                      'bg-warning-soft text-warning-foreground'
                    }`}>
                      {h.status?.toUpperCase() === 'FAILED' ? <AlertTriangle className="h-3.5 w-3.5" /> : 
                       h.status?.toUpperCase() === 'COMPLETE' ? <CheckCircle2 className="h-3.5 w-3.5" /> :
                       <Clock className="h-3.5 w-3.5" />}
                      {h.status}
                    </span>
                    <span className="text-xs text-muted-foreground">{h.created_at ? getTimeAgo(h.created_at) : 'Just now'}</span>
                  </div>
                </div>

                <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
                  <SbarBlock letter="S" label="Situation" tone="primary" text={h.situation || 'Not available'} />
                  <SbarBlock letter="B" label="Background" tone="accent" text={h.background || 'Not available'} />
                  <SbarBlock letter="A" label="Assessment" tone="warning" text={h.assessment || 'Not available'} />
                  <SbarBlock letter="R" label="Recommendation" tone="destructive" text={h.recommendation || 'Not available'} />
                </div>

                <div className="mt-5 flex justify-end">
                  <button className="inline-flex items-center gap-1 text-sm font-semibold text-primary transition-colors hover:opacity-80">
                    View details <ArrowUpRight className="h-4 w-4" />
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </AppLayout>
  );
}

function SbarBlock({
  letter,
  label,
  tone,
  text,
}: {
  letter: string;
  label: string;
  tone: keyof typeof toneMap;
  text: string;
}) {
  return (
    <div className="rounded-2xl bg-surface-muted/70 p-4">
      <div className="flex items-center gap-2.5">
        <div className={`flex h-7 w-7 items-center justify-center rounded-lg text-xs font-bold ${toneMap[tone]}`}>
          {letter}
        </div>
        <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          {label}
        </div>
      </div>
      <p className="mt-2.5 text-sm leading-relaxed text-foreground/85">{text}</p>
    </div>
  );
}
