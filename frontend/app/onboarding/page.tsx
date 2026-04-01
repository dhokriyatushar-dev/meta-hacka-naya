"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiPost } from "@/lib/api";
import { supabase } from "@/lib/supabase";

const STEPS = [
  { num: 1, title: "Identity & Background", desc: "Upload resume or describe your background", icon: "📄" },
  { num: 2, title: "Skill Assessment", desc: "What do you know? Rate your skills", icon: "🎚️" },
  { num: 3, title: "Dream Job", desc: "Paste a job description (optional)", icon: "💼" },
  { num: 4, title: "Commitment", desc: "How much time can you dedicate?", icon: "⏰" },
];

interface Skill {
  skill: string;
  level: string;
  proficiency: number;
}

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [userId, setUserId] = useState<string>("");

  // Form data
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [resumeText, setResumeText] = useState("");
  const [targetField, setTargetField] = useState("");
  const [skills, setSkills] = useState<Skill[]>([]);
  const [skillInput, setSkillInput] = useState("");
  const [skillLevel, setSkillLevel] = useState("Beginner");
  const [jobDescription, setJobDescription] = useState("");
  const [weeklyHours, setWeeklyHours] = useState(10);
  const [learningGoal, setLearningGoal] = useState("");

  // Check auth on mount
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) {
        router.push("/auth");
        return;
      }
      setUserId(session.user.id);
      setEmail(session.user.email || "");
      setName(session.user.user_metadata?.full_name || "");
    });
  }, [router]);

  const addSkill = () => {
    if (skillInput && !skills.find(s => s.skill === skillInput)) {
      const profMap: Record<string, number> = { "Beginner": 0.2, "Intermediate": 0.5, "Advanced": 0.8, "Expert": 0.95 };
      setSkills([...skills, { skill: skillInput, level: skillLevel, proficiency: profMap[skillLevel] || 0.3 }]);
      setSkillInput("");
    }
  };

  const removeSkill = (skillName: string) => {
    setSkills(skills.filter(s => s.skill !== skillName));
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError("");
    try {
      const result = await apiPost("/api/onboarding/complete", {
        name, email, resume_text: resumeText || null,
        target_field: targetField, skills,
        job_description: jobDescription || null,
        weekly_hours: weeklyHours, learning_goal: learningGoal,
        user_id: userId,
      });
      // Store student_id (now the Supabase user UUID)
      localStorage.setItem("edupath_student_id", result.student_id);
      localStorage.setItem("edupath_student_name", name);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  const FIELDS = [
    { id: "tech", label: "💻 Tech / CS", desc: "Software, AI, Data Science" },
    { id: "healthcare", label: "🏥 Healthcare", desc: "Medical AI, Clinical Data" },
    { id: "business", label: "📊 Business", desc: "Analytics, Strategy" },
    { id: "law", label: "⚖️ Law", desc: "Legal Tech, Compliance" },
    { id: "design", label: "🎨 Design", desc: "UX/UI, Design Thinking" },
  ];

  const HOUR_OPTIONS = [5, 10, 15, 20, 30];

  return (
    <div className="min-h-screen flex items-center justify-center p-6" style={{ background: "var(--bg-primary)" }}>
      <div className="w-full max-w-2xl">
        {/* Back link */}
        <Link href="/" className="inline-flex items-center gap-2 mb-8 text-sm transition-colors" style={{ color: "var(--text-secondary)" }}>
          ← Back to Home
        </Link>

        {/* Step Indicator */}
        <div className="flex items-center gap-2 mb-8">
          {STEPS.map((s) => (
            <div key={s.num} className="flex-1 flex flex-col items-center">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm transition-all ${
                step > s.num ? "step-completed" : step === s.num ? "step-active" : "step-inactive"
              }`}>
                {step > s.num ? "✓" : s.num}
              </div>
              <span className="text-[10px] mt-1" style={{ color: step >= s.num ? "var(--text-primary)" : "var(--text-secondary)" }}>{s.title}</span>
              {s.num < 4 && <div className={`h-0.5 w-full mt-2 ${step > s.num ? "bg-green-500" : ""}`} style={{ background: step > s.num ? "var(--accent-green)" : "var(--border)" }} />}
            </div>
          ))}
        </div>

        {/* Card */}
        <div className="glass-card p-8">
          <h2 className="text-2xl font-bold mb-1">{STEPS[step - 1].icon} {STEPS[step - 1].title}</h2>
          <p className="text-sm mb-6" style={{ color: "var(--text-secondary)" }}>{STEPS[step - 1].desc}</p>

          {/* ── Step 1: Identity ── */}
          {step === 1 && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Your Name</label>
                  <input type="text" value={name} onChange={(e) => setName(e.target.value)}
                    className="w-full px-4 py-3 rounded-xl outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                    style={{ background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
                    placeholder="Alex Johnson" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Email</label>
                  <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-4 py-3 rounded-xl outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                    style={{ background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
                    placeholder="alex@example.com" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Paste Your Resume <span style={{ color: "var(--text-secondary)" }}>(optional)</span></label>
                <textarea value={resumeText} onChange={(e) => setResumeText(e.target.value)}
                  className="w-full h-32 px-4 py-3 rounded-xl outline-none focus:ring-2 focus:ring-blue-500 resize-none transition-all"
                  style={{ background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
                  placeholder="Paste your resume text here, or skip this step..." />
                <p className="text-xs mt-1" style={{ color: "var(--text-secondary)" }}>AI will automatically extract your skills, education, and experience.</p>
              </div>
            </div>
          )}

          {/* ── Step 2: Skills ── */}
          {step === 2 && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">What do you want to learn?</label>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {FIELDS.map((f) => (
                    <button key={f.id} onClick={() => setTargetField(f.id)}
                      className="p-3 rounded-xl text-left transition-all"
                      style={{
                        background: targetField === f.id ? "rgba(79,110,247,0.2)" : "var(--bg-primary)",
                        border: `1px solid ${targetField === f.id ? "var(--accent-blue)" : "var(--border)"}`,
                      }}>
                      <div className="text-sm font-bold">{f.label}</div>
                      <div className="text-[10px]" style={{ color: "var(--text-secondary)" }}>{f.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Skills you already have</label>
                <div className="flex gap-2 mb-3">
                  <input type="text" value={skillInput} onChange={(e) => setSkillInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && addSkill()}
                    className="flex-1 px-4 py-2 rounded-lg outline-none"
                    style={{ background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
                    placeholder="e.g. Python, Statistics, Excel" />
                  <select value={skillLevel} onChange={(e) => setSkillLevel(e.target.value)}
                    className="px-3 py-2 rounded-lg outline-none"
                    style={{ background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)" }}>
                    <option>Beginner</option>
                    <option>Intermediate</option>
                    <option>Advanced</option>
                    <option>Expert</option>
                  </select>
                  <button onClick={addSkill} className="glow-btn !py-2 !px-4 text-sm">Add</button>
                </div>
                <div className="flex flex-wrap gap-2 min-h-[40px]">
                  {skills.map((s) => (
                    <span key={s.skill} className="px-3 py-1 rounded-full text-xs font-medium flex items-center gap-2"
                      style={{ background: "rgba(79,110,247,0.15)", color: "var(--accent-blue)", border: "1px solid rgba(79,110,247,0.3)" }}>
                      {s.skill} <span style={{ color: "var(--text-secondary)" }}>({s.level})</span>
                      <button onClick={() => removeSkill(s.skill)} className="hover:text-red-400">×</button>
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── Step 3: Job Description ── */}
          {step === 3 && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Paste a Job Description <span style={{ color: "var(--text-secondary)" }}>(optional)</span></label>
                <textarea value={jobDescription} onChange={(e) => setJobDescription(e.target.value)}
                  className="w-full h-40 px-4 py-3 rounded-xl outline-none focus:ring-2 focus:ring-blue-500 resize-none transition-all"
                  style={{ background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
                  placeholder="Paste the job description of your dream role here. AI will extract required skills and map your gaps..." />
                <p className="text-xs mt-1" style={{ color: "var(--text-secondary)" }}>
                  If skipped, your roadmap will be pure learning-focused, not job-targeted.
                </p>
              </div>
            </div>
          )}

          {/* ── Step 4: Time & Goal ── */}
          {step === 4 && (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium mb-3">Hours per week you can commit</label>
                <div className="flex gap-3">
                  {HOUR_OPTIONS.map((h) => (
                    <button key={h} onClick={() => setWeeklyHours(h)}
                      className="flex-1 py-3 rounded-xl font-bold text-sm transition-all"
                      style={{
                        background: weeklyHours === h ? "rgba(79,110,247,0.2)" : "var(--bg-primary)",
                        border: `1px solid ${weeklyHours === h ? "var(--accent-blue)" : "var(--border)"}`,
                        color: weeklyHours === h ? "var(--accent-blue)" : "var(--text-secondary)",
                      }}>
                      {h}{h === 30 ? "+" : ""}h
                    </button>
                  ))}
                </div>
                <p className="text-xs mt-2" style={{ color: "var(--text-secondary)" }}>
                  {weeklyHours < 10 ? "💡 5+ hours recommended for steady progress" : weeklyHours >= 20 ? "🔥 Great commitment! You'll learn fast!" : "✅ Good pace for consistent learning"}
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Your Learning Goal</label>
                <textarea value={learningGoal} onChange={(e) => setLearningGoal(e.target.value)}
                  className="w-full h-24 px-4 py-3 rounded-xl outline-none focus:ring-2 focus:ring-blue-500 resize-none transition-all"
                  style={{ background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
                  placeholder="e.g. Become an ML Engineer, transition from medicine to AI, land a Data Analyst role..." />
              </div>
            </div>
          )}

          {/* Error */}
          {error && <p className="text-sm mt-4 px-3 py-2 rounded-lg" style={{ background: "rgba(239,68,68,0.1)", color: "var(--accent-red)" }}>{error}</p>}

          {/* Navigation */}
          <div className="mt-8 flex justify-between items-center">
            {step > 1 ? (
              <button onClick={() => setStep(step - 1)} className="px-6 py-2 font-medium transition-colors" style={{ color: "var(--text-secondary)" }}>← Back</button>
            ) : <div />}

            {step < 4 ? (
              <button onClick={() => setStep(step + 1)}
                disabled={step === 2 && !targetField}
                className="glow-btn disabled:opacity-50">
                Next →
              </button>
            ) : (
              <button onClick={handleSubmit} disabled={loading || !learningGoal}
                className="glow-btn disabled:opacity-50">
                {loading ? "Creating Your Path..." : "🚀 Generate My Roadmap"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
