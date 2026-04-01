"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { apiGet, apiPost } from "@/lib/api";

type Tab = "roadmap" | "quizzes" | "badges" | "career";

interface StudentData {
  name: string;
  target_field: string;
  learning_goal: string;
  completed_topics: string[];
  quiz_history: any[];
  completed_projects: string[];
  badges: any[];
  job_readiness_score: number;
  weekly_hours: number;
  quiz_streak: number;
}

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState<Tab>("roadmap");
  const [studentId, setStudentId] = useState<string>("");
  const [student, setStudent] = useState<StudentData | null>(null);
  const [roadmap, setRoadmap] = useState<any>(null);
  const [quiz, setQuiz] = useState<any>(null);
  const [quizAnswers, setQuizAnswers] = useState<number[]>([]);
  const [quizResult, setQuizResult] = useState<any>(null);
  const [badges, setBadges] = useState<any>(null);
  const [career, setCareer] = useState<any>(null);
  const [events, setEvents] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const id = localStorage.getItem("edupath_student_id");
    if (id) {
      setStudentId(id);
      loadStudentData(id);
    }
  }, []);

  const loadStudentData = async (id: string) => {
    try {
      const data = await apiGet(`/api/onboarding/profile/${id}`);
      setStudent(data);
    } catch (err) {
      console.error("Failed to load student data");
    }
  };

  const generateRoadmap = async () => {
    setLoading(true);
    try {
      const data = await apiPost("/api/roadmap/generate", { student_id: studentId });
      setRoadmap(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadRoadmap = async () => {
    try {
      const data = await apiGet(`/api/roadmap/${studentId}`);
      setRoadmap(data);
    } catch {
      // No cached roadmap
    }
  };

  const generateQuiz = async (topicId: string) => {
    setLoading(true);
    setQuizResult(null);
    setQuizAnswers([]);
    try {
      const data = await apiPost("/api/quiz/generate", { student_id: studentId, topic_id: topicId });
      setQuiz(data);
      setQuizAnswers(new Array(data.questions?.length || 0).fill(-1));
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const submitQuiz = async () => {
    if (!quiz) return;
    setLoading(true);
    try {
      const data = await apiPost("/api/quiz/submit", {
        student_id: studentId,
        topic_id: quiz.topic_id,
        questions: quiz.questions,
        answers: quizAnswers,
      });
      setQuizResult(data);
      loadStudentData(studentId);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadBadges = async () => {
    try {
      const data = await apiGet(`/api/badges/${studentId}`);
      setBadges(data);
    } catch (err) {
      console.error("Failed to load badges");
    }
  };

  const loadCareer = async () => {
    try {
      const [readiness, evts] = await Promise.all([
        apiGet(`/api/career/readiness/${studentId}`),
        apiGet(`/api/career/events/${studentId}`),
      ]);
      setCareer(readiness);
      setEvents(evts);
    } catch (err) {
      console.error("Failed to load career data");
    }
  };

  useEffect(() => {
    if (!studentId) return;
    if (activeTab === "roadmap") loadRoadmap();
    if (activeTab === "badges") loadBadges();
    if (activeTab === "career") loadCareer();
  }, [activeTab, studentId]);

  // Helper: Convert a human-readable skill name to a topic_id
  const skillToTopicId = (skill: string): string => {
    return skill.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
  };

  // Helper: Find the best matching topic ID for a week
  const getTopicIdForWeek = (week: any): string => {
    // First try the skillsCovered array
    if (week.skillsCovered && week.skillsCovered.length > 0) {
      return skillToTopicId(week.skillsCovered[0]);
    }
    // Fall back to the title
    return skillToTopicId(week.title);
  };

  const TABS: { id: Tab; icon: string; label: string }[] = [
    { id: "roadmap", icon: "🗺️", label: "Roadmap" },
    { id: "quizzes", icon: "📝", label: "Quizzes" },
    { id: "badges", icon: "🏆", label: "Badges" },
    { id: "career", icon: "💼", label: "Career" },
  ];

  if (!studentId) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg-primary)" }}>
        <div className="glass-card p-8 text-center max-w-md">
          <div className="text-4xl mb-4">🎓</div>
          <h2 className="text-2xl font-bold mb-2">Welcome to EduPath AI</h2>
          <p className="mb-6" style={{ color: "var(--text-secondary)" }}>Complete onboarding to access your dashboard.</p>
          <Link href="/onboarding" className="glow-btn inline-block">Start Onboarding →</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex" style={{ background: "var(--bg-primary)" }}>
      {/* ── Sidebar ── */}
      <aside className="w-64 p-4 flex flex-col gap-2 fixed h-full" style={{ background: "var(--bg-secondary)", borderRight: "1px solid var(--border)" }}>
        <div className="flex items-center gap-2 px-4 py-3 mb-4">
          <span className="text-xl">🎓</span>
          <span className="font-bold gradient-text">EduPath AI</span>
        </div>

        {/* Student info */}
        {student && (
          <div className="px-4 py-3 rounded-xl mb-4" style={{ background: "var(--bg-card)" }}>
            <div className="text-sm font-bold">{student.name || "Student"}</div>
            <div className="text-xs" style={{ color: "var(--text-secondary)" }}>{student.target_field?.toUpperCase()} • {student.weekly_hours}h/week</div>
            <div className="mt-2">
              <div className="text-[10px]" style={{ color: "var(--text-secondary)" }}>Job Readiness</div>
              <div className="progress-bar mt-1">
                <div className="progress-fill" style={{ width: `${(student.job_readiness_score || 0) * 100}%` }} />
              </div>
              <div className="text-xs font-bold mt-1 gradient-text">{Math.round((student.job_readiness_score || 0) * 100)}%</div>
            </div>
          </div>
        )}

        {TABS.map((tab) => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`sidebar-item flex items-center gap-3 text-sm ${activeTab === tab.id ? "sidebar-item-active" : ""}`}>
            <span>{tab.icon}</span> {tab.label}
          </button>
        ))}

        <div className="mt-auto">
          <Link href="/" className="sidebar-item flex items-center gap-3 text-sm">
            <span>🏠</span> Home
          </Link>
        </div>
      </aside>

      {/* ── Main Content ── */}
      <main className="flex-1 ml-64 p-8">
        {error && (
          <div className="mb-4 px-4 py-2 rounded-lg" style={{ background: "rgba(239,68,68,0.1)", color: "var(--accent-red)" }}>
            {error}
            <button onClick={() => setError("")} className="ml-4 font-bold">×</button>
          </div>
        )}

        {/* ═══ ROADMAP TAB ═══ */}
        {activeTab === "roadmap" && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-2xl font-bold">🗺️ Your Learning Roadmap</h1>
                <p className="text-sm" style={{ color: "var(--text-secondary)" }}>Personalized path generated by AI</p>
              </div>
              <button onClick={generateRoadmap} disabled={loading} className="glow-btn !text-sm disabled:opacity-50">
                {loading ? "Generating..." : roadmap ? "🔄 Regenerate" : "✨ Generate Roadmap"}
              </button>
            </div>

            {roadmap?.weeks ? (
              <div>
                <div className="space-y-4">
                  {roadmap.weeks.map((week: any, i: number) => {
                    const topicId = getTopicIdForWeek(week);
                    return (
                      <div key={i} className="glass-card p-6" style={{ animationDelay: `${i * 0.05}s` }}>
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-3 mb-2">
                              <span className="px-2 py-0.5 rounded-full text-xs font-bold" style={{ background: "rgba(79,110,247,0.2)", color: "var(--accent-blue)" }}>
                                Week {week.weekNumber || i + 1}
                              </span>
                              <h3 className="font-bold">{week.title}</h3>
                            </div>
                            {week.learningObjectives && (
                              <ul className="text-sm space-y-1 ml-4" style={{ color: "var(--text-secondary)" }}>
                                {week.learningObjectives.map((obj: string, j: number) => (
                                  <li key={j}>• {obj}</li>
                                ))}
                              </ul>
                            )}
                            {week.skillsCovered && (
                              <div className="flex flex-wrap gap-1 mt-2">
                                {week.skillsCovered.map((skill: string, j: number) => (
                                  <span key={j} className="px-2 py-0.5 rounded text-[10px]" style={{ background: "rgba(139,92,246,0.15)", color: "var(--accent-purple)" }}>
                                    {skill}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                          <div className="flex flex-col gap-2 ml-4">
                            <Link href={`/dashboard/topic?id=${topicId}`}
                              className="text-xs px-3 py-1.5 rounded-lg font-bold text-center whitespace-nowrap" style={{ background: "rgba(79,110,247,0.15)", color: "var(--accent-blue)" }}>
                              📚 Study Topic
                            </Link>
                            <button onClick={() => { setActiveTab("quizzes"); generateQuiz(topicId); }}
                              className="text-xs px-3 py-1.5 rounded-lg font-bold whitespace-nowrap" style={{ background: "rgba(34,197,94,0.15)", color: "var(--accent-green)" }}>
                              📝 Take Quiz
                            </button>
                          </div>
                        </div>
                        {week.mini_project && (
                          <div className="mt-3 p-3 rounded-lg" style={{ background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.2)" }}>
                            <div className="text-xs font-bold" style={{ color: "var(--accent-amber)" }}>🛠️ Mini Project: {week.mini_project.title}</div>
                            <div className="text-xs mt-1" style={{ color: "var(--text-secondary)" }}>{week.mini_project.description}</div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* ── Capstone Projects Section ── */}
                {roadmap.capstone_projects && roadmap.capstone_projects.length > 0 && (
                  <div className="mt-10">
                    <div className="flex items-center gap-3 mb-6">
                      <span className="text-2xl">🏆</span>
                      <div>
                        <h2 className="text-xl font-bold">Capstone Projects</h2>
                        <p className="text-sm" style={{ color: "var(--text-secondary)" }}>Complete these to demonstrate mastery & earn your final badges</p>
                      </div>
                    </div>
                    <div className="grid md:grid-cols-2 gap-6">
                      {roadmap.capstone_projects.map((cap: any, i: number) => (
                        <div key={i} className="glass-card p-6 relative overflow-hidden" style={{ border: "1px solid rgba(245,158,11,0.3)" }}>
                          <div className="absolute top-0 right-0 px-3 py-1 rounded-bl-lg text-[10px] font-bold" style={{ background: "rgba(245,158,11,0.2)", color: "var(--accent-amber)" }}>
                            CAPSTONE {i + 1}
                          </div>
                          <h3 className="font-bold text-lg mb-2 mt-2">{cap.title}</h3>
                          <p className="text-sm mb-3" style={{ color: "var(--text-secondary)" }}>{cap.description}</p>
                          {cap.expected_output && (
                            <div className="text-xs mb-3 p-2 rounded" style={{ background: "var(--bg-primary)" }}>
                              <span className="font-bold">Expected Output:</span> {cap.expected_output}
                            </div>
                          )}
                          {cap.requirements && (
                            <div className="flex flex-wrap gap-1 mb-3">
                              {cap.requirements.map((req: string, j: number) => (
                                <span key={j} className="px-2 py-0.5 rounded text-[10px]" style={{ background: "rgba(139,92,246,0.15)", color: "var(--accent-purple)" }}>
                                  {req}
                                </span>
                              ))}
                            </div>
                          )}
                          {cap.skills_tested && (
                            <div className="flex flex-wrap gap-1">
                              {cap.skills_tested.map((skill: string, j: number) => (
                                <span key={j} className="px-2 py-0.5 rounded text-[10px]" style={{ background: "rgba(79,110,247,0.1)", color: "var(--accent-blue)" }}>
                                  ✓ {skill}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="glass-card p-12 text-center">
                <div className="text-4xl mb-4 animate-float">🗺️</div>
                <h3 className="text-lg font-bold mb-2">No Roadmap Yet</h3>
                <p className="text-sm" style={{ color: "var(--text-secondary)" }}>Click &quot;Generate Roadmap&quot; to create your personalized learning path.</p>
              </div>
            )}
          </div>
        )}

        {/* ═══ QUIZZES TAB ═══ */}
        {activeTab === "quizzes" && (
          <div>
            <h1 className="text-2xl font-bold mb-6">📝 Adaptive Quizzes</h1>

            {!quiz && !quizResult && (
              <div className="glass-card p-8 text-center">
                <div className="text-4xl mb-4">📝</div>
                <h3 className="text-lg font-bold mb-2">Take a Quiz</h3>
                <p className="text-sm mb-4" style={{ color: "var(--text-secondary)" }}>Select a topic from your roadmap to test your knowledge.</p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {["python_basics", "data_structures", "machine_learning", "statistics", "web_development"].map((t) => (
                    <button key={t} onClick={() => generateQuiz(t)}
                      className="px-4 py-2 rounded-lg text-sm transition-all hover:scale-105"
                      style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
                      {t.replace(/_/g, " ")}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {quiz && !quizResult && (
              <div className="space-y-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-bold">{quiz.topic_name}</h3>
                  <span className="px-3 py-1 rounded-full text-xs" style={{ background: "rgba(79,110,247,0.15)", color: "var(--accent-blue)" }}>
                    {quiz.difficulty?.toUpperCase()}
                  </span>
                </div>

                {quiz.questions?.map((q: any, i: number) => (
                  <div key={i} className="glass-card p-6">
                    <h4 className="font-medium mb-3">Q{i + 1}. {q.question}</h4>
                    <div className="space-y-2">
                      {q.options?.map((opt: string, j: number) => (
                        <button key={j} onClick={() => {
                          const newAnswers = [...quizAnswers];
                          newAnswers[i] = j;
                          setQuizAnswers(newAnswers);
                        }}
                          className="w-full text-left px-4 py-3 rounded-lg text-sm transition-all"
                          style={{
                            background: quizAnswers[i] === j ? "rgba(79,110,247,0.2)" : "var(--bg-primary)",
                            border: `1px solid ${quizAnswers[i] === j ? "var(--accent-blue)" : "var(--border)"}`,
                          }}>
                          {opt}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}

                <button onClick={submitQuiz} disabled={quizAnswers.includes(-1) || loading}
                  className="glow-btn w-full disabled:opacity-50">
                  {loading ? "Scoring..." : "Submit Answers"}
                </button>
              </div>
            )}

            {quizResult && (
              <div className="glass-card p-8 text-center">
                <div className="text-5xl mb-4">{quizResult.passed ? "🎉" : quizResult.score >= 50 ? "📖" : "💪"}</div>
                <h3 className="text-2xl font-bold mb-2">
                  Score: <span className={quizResult.passed ? "text-green-400" : quizResult.score >= 50 ? "text-amber-400" : "text-red-400"}>
                    {quizResult.score}%
                  </span>
                </h3>
                <p className="mb-4" style={{ color: "var(--text-secondary)" }}>{quizResult.message}</p>
                <div className="text-sm mb-6" style={{ color: "var(--text-secondary)" }}>
                  {quizResult.correct_answers}/{quizResult.total_questions} correct
                </div>

                {/* Download Notes / Resources */}
                <div className="mb-6 p-4 rounded-xl" style={{ background: "var(--bg-primary)", border: "1px solid var(--border)" }}>
                  <h4 className="text-sm font-bold mb-2">📥 Download Study Resources</h4>
                  <div className="flex flex-wrap gap-2 justify-center">
                    <a href={`https://www.google.com/search?q=${quiz?.topic_name?.replace(/ /g, '+')}+cheat+sheet+pdf`}
                      target="_blank" rel="noopener noreferrer"
                      className="px-4 py-2 rounded-lg text-xs font-bold transition-all hover:scale-105"
                      style={{ background: "rgba(79,110,247,0.15)", color: "var(--accent-blue)" }}>
                      📄 Cheat Sheet
                    </a>
                    <a href={`https://www.google.com/search?q=${quiz?.topic_name?.replace(/ /g, '+')}+study+notes+pdf`}
                      target="_blank" rel="noopener noreferrer"
                      className="px-4 py-2 rounded-lg text-xs font-bold transition-all hover:scale-105"
                      style={{ background: "rgba(139,92,246,0.15)", color: "var(--accent-purple)" }}>
                      📝 Study Notes
                    </a>
                    <a href={`https://www.google.com/search?q=${quiz?.topic_name?.replace(/ /g, '+')}+practice+exercises`}
                      target="_blank" rel="noopener noreferrer"
                      className="px-4 py-2 rounded-lg text-xs font-bold transition-all hover:scale-105"
                      style={{ background: "rgba(34,197,94,0.15)", color: "var(--accent-green)" }}>
                      🏋️ Practice Exercises
                    </a>
                  </div>
                </div>

                <div className="flex gap-3 justify-center">
                  <button onClick={() => { setQuiz(null); setQuizResult(null); }} className="glow-btn !text-sm">
                    Take Another Quiz
                  </button>
                  {!quizResult.passed && (
                    <button onClick={() => { setQuizResult(null); setQuizAnswers(new Array(quiz?.questions?.length || 0).fill(-1)); }}
                      className="px-6 py-2 rounded-lg text-sm" style={{ border: "1px solid var(--border)" }}>
                      Retry
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ═══ BADGES TAB ═══ */}
        {activeTab === "badges" && (
          <div>
            <h1 className="text-2xl font-bold mb-2">🏆 Badges & Achievements</h1>
            <p className="text-sm mb-6" style={{ color: "var(--text-secondary)" }}>Collect them all to prove your mastery!</p>
            {badges ? (
              <div>
                <div className="glass-card p-4 mb-6 flex items-center justify-between">
                  <div>
                    <span className="text-2xl font-bold gradient-text">{badges.earned_count}</span>
                    <span className="text-sm ml-2" style={{ color: "var(--text-secondary)" }}>/ {badges.total_count} badges earned</span>
                  </div>
                  <div className="progress-bar w-48">
                    <div className="progress-fill" style={{ width: `${(badges.earned_count / badges.total_count) * 100}%` }} />
                  </div>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {badges.badges?.map((badge: any, i: number) => (
                    <div key={i} className={`p-4 rounded-2xl text-center transition-all hover:scale-105 ${badge.earned ? "badge-earned" : "badge-locked"}`}>
                      <div className="text-3xl mb-2">{badge.icon}</div>
                      <h4 className="text-sm font-bold">{badge.name}</h4>
                      <p className="text-[10px] mt-1" style={{ color: "var(--text-secondary)" }}>{badge.description}</p>
                      {badge.earned && <span className="inline-block mt-2 text-[10px] font-bold" style={{ color: "var(--accent-green)" }}>✓ Earned</span>}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="glass-card p-8 text-center">
                <div className="text-4xl mb-4 animate-float">🏆</div>
                <p style={{ color: "var(--text-secondary)" }}>Loading badges...</p>
              </div>
            )}
          </div>
        )}

        {/* ═══ CAREER TAB ═══ */}
        {activeTab === "career" && (
          <div>
            <h1 className="text-2xl font-bold mb-6">💼 Job Readiness & Career</h1>

            {career && (
              <div className="grid md:grid-cols-2 gap-6 mb-8">
                <div className="glass-card p-6">
                  <h3 className="font-bold mb-4">Job Readiness Score</h3>
                  <div className="text-center">
                    <div className="text-5xl font-bold gradient-text">{Math.round(career.job_readiness_score * 100)}%</div>
                    <div className="progress-bar mt-4 h-3">
                      <div className="progress-fill" style={{ width: `${career.job_readiness_score * 100}%` }} />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3 mt-6 text-sm">
                    <div className="p-3 rounded-lg" style={{ background: "var(--bg-primary)" }}>
                      <div style={{ color: "var(--text-secondary)" }}>Topics</div>
                      <div className="font-bold">{career.breakdown?.topics_completed || 0}</div>
                    </div>
                    <div className="p-3 rounded-lg" style={{ background: "var(--bg-primary)" }}>
                      <div style={{ color: "var(--text-secondary)" }}>Quiz Avg</div>
                      <div className="font-bold">{career.breakdown?.average_quiz_score || 0}%</div>
                    </div>
                    <div className="p-3 rounded-lg" style={{ background: "var(--bg-primary)" }}>
                      <div style={{ color: "var(--text-secondary)" }}>Capstones</div>
                      <div className="font-bold">{career.breakdown?.projects_completed || 0}</div>
                    </div>
                    <div className="p-3 rounded-lg" style={{ background: "var(--bg-primary)" }}>
                      <div style={{ color: "var(--text-secondary)" }}>Streak</div>
                      <div className="font-bold">🔥 {career.breakdown?.quiz_streak || 0}</div>
                    </div>
                  </div>
                </div>

                <div className="glass-card p-6">
                  <h3 className="font-bold mb-4">Interview Prep</h3>
                  {career.interview_prep_unlocked ? (
                    <div className="text-center p-6">
                      <div className="text-3xl mb-2">🎯</div>
                      <p className="font-bold text-green-400">Unlocked!</p>
                      <p className="text-sm" style={{ color: "var(--text-secondary)" }}>You&apos;re ready for interview preparation.</p>
                    </div>
                  ) : (
                    <div className="text-center p-6">
                      <div className="text-3xl mb-2 opacity-50">🔒</div>
                      <p className="font-bold" style={{ color: "var(--text-secondary)" }}>Locked</p>
                      <p className="text-sm" style={{ color: "var(--text-secondary)" }}>Reach 70% job readiness to unlock.</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {events && (
              <div>
                <h3 className="font-bold mb-4">🎪 Recommended Events & Opportunities</h3>
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {events.events?.map((event: any, i: number) => (
                    <a key={i} href={event.url} target="_blank" rel="noopener noreferrer" className="glass-card p-4 block hover:scale-[1.02] transition-transform">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold" style={{
                          background: event.type === "hackathon" ? "rgba(139,92,246,0.2)" : event.type === "conference" ? "rgba(79,110,247,0.2)" : "rgba(34,197,94,0.2)",
                          color: event.type === "hackathon" ? "var(--accent-purple)" : event.type === "conference" ? "var(--accent-blue)" : "var(--accent-green)",
                        }}>{event.type}</span>
                      </div>
                      <h4 className="font-bold text-sm">{event.name}</h4>
                      <p className="text-[10px] mt-1" style={{ color: "var(--text-secondary)" }}>{event.url}</p>
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
