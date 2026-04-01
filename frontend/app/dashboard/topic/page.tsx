"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Suspense } from "react";
import Link from "next/link";
import { apiGet, apiPost } from "@/lib/api";
import { SOURCE_CONFIG } from "@/lib/resourceUtils";

interface ResourceCard {
  title: string;
  url: string;
  source: string;
  description: string;
  duration_estimate: string;
  resource_type: string;
}

interface TopicData {
  topic_id: string;
  topic_name: string;
  ai_summary: string;
  resources: ResourceCard[];
  can_mark_complete: boolean;
  quiz_unlocked: boolean;
}

function TopicContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const topicId = searchParams.get("id") as string;
  
  const [topicData, setTopicData] = useState<TopicData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [canMarkComplete, setCanMarkComplete] = useState(false);
  const [markingComplete, setMarkingComplete] = useState(false);

  useEffect(() => {
    const fetchTopic = async () => {
      try {
        const studentId = localStorage.getItem("edupath_student_id") || "";
        const data = await apiGet(`/resources/${topicId}?student_id=${studentId}`);
        setTopicData(data);
        setCanMarkComplete(data.can_mark_complete);
      } catch (err: any) {
        setError(err.message || "Failed to load topic resources");
      } finally {
        setLoading(false);
      }
    };
    
    if (topicId) {
      fetchTopic();
    }
  }, [topicId]);

  const handleResourceClick = async (url: string) => {
    window.open(url, "_blank");

    const studentId = localStorage.getItem("edupath_student_id");
    if (!studentId) return;

    try {
      const data = await apiPost(`/resources/${topicId}/link-clicked`, {
        student_id: studentId,
        resource_url: url
      });
      if (data.can_mark_complete) {
        setCanMarkComplete(true);
      }
    } catch (err) {
      console.error("Failed to record link click:", err);
    }
  };

  const handleMarkComplete = async () => {
    const studentId = localStorage.getItem("edupath_student_id");
    if (!studentId) return;

    setMarkingComplete(true);
    try {
      const data = await apiPost(`/resources/${topicId}/mark-complete`, {
        student_id: studentId
      });
      
      if (data.quiz_unlocked) {
        // Navigate back to dashboard where they can take the quiz
        // Optional: Could pass a query param or state to open the quiz tab
        router.push('/dashboard');
      }
    } catch (err: any) {
      alert(err.message || "Failed to mark complete. Did you click a resource link first?");
    } finally {
      setMarkingComplete(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen p-8" style={{ background: "var(--bg-primary)" }}>
        <Link href="/dashboard" className="text-sm mb-6 inline-block" style={{ color: "var(--text-secondary)" }}>← Back to Dashboard</Link>
        <div className="glass-card p-8 animate-pulse">
          <div className="h-8 bg-gray-700 w-1/3 rounded mb-4"></div>
          <div className="h-4 bg-gray-700 w-1/4 rounded mb-8"></div>
          <div className="h-32 bg-gray-700 w-full rounded mb-8"></div>
          <div className="grid md:grid-cols-3 gap-4">
            <div className="h-24 bg-gray-700 rounded"></div>
            <div className="h-24 bg-gray-700 rounded"></div>
            <div className="h-24 bg-gray-700 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen p-8" style={{ background: "var(--bg-primary)" }}>
        <Link href="/dashboard" className="text-sm mb-6 inline-block" style={{ color: "var(--text-secondary)" }}>← Back to Dashboard</Link>
        <div className="glass-card p-8 text-center text-red-400">
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!topicData) return null;

  return (
    <div className="min-h-screen p-6 md:p-12" style={{ background: "var(--bg-primary)" }}>
      <Link href="/dashboard" className="text-sm mb-6 inline-block hover:underline" style={{ color: "var(--text-secondary)" }}>
        ← Back to Roadmap
      </Link>

      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Topic: {topicData.topic_name}</h1>
        <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
          {/* Estimated time could be aggregated from resources */}
          Select a free resource below to start learning.
        </p>
      </div>

      <div className="glass-card p-6 md:p-8 mb-8">
        <h2 className="text-sm font-bold opacity-50 mb-4 tracking-wider">AI SUMMARY</h2>
        <div className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
          {topicData.ai_summary.split('\n\n').map((paragraph, i) => (
            <p key={i} className="mb-4">{paragraph}</p>
          ))}
        </div>
      </div>

      <h2 className="text-sm font-bold opacity-50 mb-4 tracking-wider">FREE COURSES & RESOURCES</h2>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {topicData.resources.map((res, i) => {
          const config = SOURCE_CONFIG[res.source] || SOURCE_CONFIG["Other"];
          return (
            <div key={i} className="glass-card p-5 flex flex-col h-full hover:scale-[1.02] transition-transform">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold px-2 py-1 rounded" style={{ backgroundColor: `${config.color}20`, color: config.color }}>
                  {config.label}
                </span>
                <span className="text-xs opacity-50">{res.duration_estimate}</span>
              </div>
              <h3 className="font-bold text-sm mb-2 line-clamp-2">{res.title}</h3>
              <p className="text-xs opacity-70 mb-4 flex-grow line-clamp-3">{res.description}</p>
              
              <button 
                onClick={() => handleResourceClick(res.url)}
                className="w-full text-center py-2 rounded-lg text-sm font-bold transition-all mt-auto"
                style={{ background: `${config.color}15`, color: config.color, border: `1px solid ${config.color}30` }}
              >
                Go to Course →
              </button>
            </div>
          );
        })}
      </div>

      <div className="glass-card p-6 flex flex-col md:flex-row items-center justify-between gap-4">
        <div>
          <h3 className="font-bold">Ready to take the quiz?</h3>
          <p className="text-xs opacity-70">Mark this topic as complete to unlock the quiz on your dashboard.</p>
        </div>
        
        {topicData.quiz_unlocked ? (
          <Link href="/dashboard" className="glow-btn !text-sm whitespace-nowrap">
            Take Quiz →
          </Link>
        ) : (
          <button 
            onClick={handleMarkComplete}
            disabled={!canMarkComplete || markingComplete}
            className={`px-6 py-3 rounded-lg text-sm font-bold whitespace-nowrap transition-all ${
              canMarkComplete && !markingComplete ? 'glow-btn' : 'opacity-40 cursor-not-allowed bg-gray-800'
            }`}
          >
            {markingComplete ? "Marking..." : "Mark as Complete ✓"}
          </button>
        )}
      </div>
    </div>
  );
}

export default function TopicPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen p-8 text-center" style={{ background: "var(--bg-primary)", color: "var(--text-secondary)" }}>
        Loading Topic...
      </div>
    }>
      <TopicContent />
    </Suspense>
  );
}
