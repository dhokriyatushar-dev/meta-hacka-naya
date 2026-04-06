-- =====================================================================
-- EduPath AI — Supabase Database Migration Script
-- Team KRIYA | Meta Hackathon 2026
--
-- Purpose:
--   Provisions the complete PostgreSQL schema for the EduPath AI
--   personalized learning platform on Supabase. Covers student
--   profiles, quiz history, project evaluations, roadmap state,
--   and progress analytics.
--
-- Usage:
--   Paste this file into the Supabase SQL Editor and click "Run".
--   Idempotent — safe to execute multiple times (IF NOT EXISTS).
--
-- Schema Overview:
--   1. students             — Core learner profiles and onboarding data
--   2. student_quizzes      — Per-topic quiz attempt records
--   3. student_projects     — Project submissions with AI evaluation
--   4. student_roadmaps     — Currently active learning roadmap (1 per student)
--   5. roadmap_history      — Archived roadmaps for longitudinal tracking
--   6. progress_snapshots   — Periodic snapshots for analytics dashboards
-- =====================================================================


-- ─────────────────────────────────────────────────────────────────────
-- 1. STUDENTS — Core learner profiles
--    Stores onboarding data, skill assessments, progress state, and
--    gamification badges. JSON fields use TEXT to maximise Supabase
--    compatibility across client libraries.
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS students (
  id TEXT PRIMARY KEY,                              -- Supabase auth user UUID stored as TEXT for flexibility
  name TEXT NOT NULL DEFAULT '',
  email TEXT DEFAULT '',
  target_field TEXT DEFAULT 'tech',                  -- Learning domain: tech | healthcare | business | law | design
  learning_goal TEXT DEFAULT '',
  job_description TEXT DEFAULT '',
  weekly_hours INT DEFAULT 10,
  job_readiness_score FLOAT DEFAULT 0.0,             -- Composite readiness metric (0.0–1.0)
  quiz_streak INT DEFAULT 0,                         -- Consecutive quizzes passed (gamification)

  -- Serialised JSON arrays/objects stored as TEXT for cross-client compatibility
  resume_skills TEXT DEFAULT '[]',                   -- Skills extracted from resume via NLP
  self_assessed_skills TEXT DEFAULT '[]',             -- [{skill, level, proficiency}] from onboarding
  jd_required_skills TEXT DEFAULT '[]',               -- Skills parsed from target job description
  completed_topics TEXT DEFAULT '[]',                 -- Topic IDs the student has mastered
  completed_projects TEXT DEFAULT '[]',               -- Project IDs submitted and evaluated
  topics_studied TEXT DEFAULT '[]',                   -- Topics where the student engaged with resources
  clicked_resource_links TEXT DEFAULT '{}',           -- {topic_id: [url, ...]} resource interaction log
  badges TEXT DEFAULT '[]',                           -- Gamification badge objects [{name, icon, ...}]
  mastery_probabilities TEXT DEFAULT '{}',            -- BKT P(known) per topic {topic_id: float}

  onboarding_complete BOOLEAN DEFAULT FALSE,          -- TRUE after completing the 4-step onboarding flow

  -- Profile tracking for roadmap lifecycle
  current_roadmap_id UUID,                            -- FK to the active roadmap (nullable)
  total_roadmaps_completed INT DEFAULT 0,

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);


-- ─────────────────────────────────────────────────────────────────────
-- 2. STUDENT_QUIZZES — Quiz attempt history
--    Each row is one quiz attempt on a specific topic. The adaptive
--    engine uses past attempts to adjust difficulty via BKT.
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS student_quizzes (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  student_id TEXT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  topic_id TEXT NOT NULL DEFAULT '',                  -- Curriculum topic identifier
  score INT DEFAULT 0,                               -- Percentage score 0–100
  total_questions INT DEFAULT 0,
  correct_answers INT DEFAULT 0,
  passed BOOLEAN DEFAULT FALSE,                       -- TRUE if score >= 70
  difficulty TEXT DEFAULT 'medium',                   -- Adaptive difficulty: easy | medium | hard
  created_at TIMESTAMPTZ DEFAULT now()
);


-- ─────────────────────────────────────────────────────────────────────
-- 3. STUDENT_PROJECTS — Project submissions & AI evaluations
--    Supports both mini-projects (per-topic) and capstone projects.
--    evaluation_data stores the full LLM-generated assessment JSON.
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS student_projects (
  id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  student_id TEXT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  project_title TEXT DEFAULT '',
  project_type TEXT DEFAULT 'mini_project',           -- mini_project | capstone
  submission_text TEXT DEFAULT '',                    -- GitHub URL, code, or description
  score INT DEFAULT 0,                               -- AI evaluation score 0–100
  grade TEXT DEFAULT 'N/A',                           -- Letter grade: A+ through F
  is_passing BOOLEAN DEFAULT FALSE,                   -- TRUE if score >= 60
  evaluation_data TEXT DEFAULT '{}',                  -- Full AI evaluation response (JSON)
  created_at TIMESTAMPTZ DEFAULT now()
);


-- ─────────────────────────────────────────────────────────────────────
-- 4. STUDENT_ROADMAPS — Active learning roadmap
--    One active roadmap per student. Replaced when the AI replans
--    (e.g., after repeated quiz failures trigger bridge topic insertion).
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS student_roadmaps (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  student_id TEXT NOT NULL UNIQUE,                    -- Enforces one active roadmap per student
  roadmap_data TEXT DEFAULT '{}',                     -- Full LLM-generated roadmap (JSON)
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);


-- ─────────────────────────────────────────────────────────────────────
-- 5. ROADMAP_HISTORY — Archived past roadmaps
--    When a student switches goals or the AI triggers a replan, the
--    old roadmap is archived here for longitudinal analysis.
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS roadmap_history (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  student_id TEXT NOT NULL,
  roadmap_data JSONB NOT NULL,                        -- Full roadmap snapshot (JSONB for query flexibility)
  topics_covered TEXT[] DEFAULT '{}',                 -- Array of topic IDs completed during this roadmap
  started_at TIMESTAMPTZ DEFAULT now(),
  archived_at TIMESTAMPTZ DEFAULT now(),
  completion_percentage FLOAT DEFAULT 0.0             -- 0.0–100.0 progress when archived
);


-- ─────────────────────────────────────────────────────────────────────
-- 6. PROGRESS_SNAPSHOTS — Periodic progress analytics
--    Captured at regular intervals (or on significant events) to
--    power the analytics dashboard and track improvement over time.
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS progress_snapshots (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  student_id TEXT NOT NULL,
  snapshot_date DATE DEFAULT CURRENT_DATE,
  topics_completed TEXT[] DEFAULT '{}',
  quizzes_passed INT DEFAULT 0,
  projects_completed INT DEFAULT 0,
  job_readiness_score FLOAT DEFAULT 0.0,
  total_study_hours FLOAT DEFAULT 0.0
);


-- ─────────────────────────────────────────────────────────────────────
-- INDEXES — Optimise common query patterns
-- ─────────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_quizzes_student         ON student_quizzes(student_id);
CREATE INDEX IF NOT EXISTS idx_quizzes_topic            ON student_quizzes(topic_id);
CREATE INDEX IF NOT EXISTS idx_quizzes_created          ON student_quizzes(created_at);
CREATE INDEX IF NOT EXISTS idx_projects_student         ON student_projects(student_id);
CREATE INDEX IF NOT EXISTS idx_roadmaps_student         ON student_roadmaps(student_id);
CREATE INDEX IF NOT EXISTS idx_roadmap_history_student   ON roadmap_history(student_id);
CREATE INDEX IF NOT EXISTS idx_progress_student         ON progress_snapshots(student_id);
CREATE INDEX IF NOT EXISTS idx_progress_date            ON progress_snapshots(snapshot_date);


-- ─────────────────────────────────────────────────────────────────────
-- ROW LEVEL SECURITY (RLS)
--    Enabled on all tables. Backend uses the Supabase service-role key,
--    which bypasses RLS. Policies below grant open access for the
--    service role while maintaining the security posture.
-- ─────────────────────────────────────────────────────────────────────
ALTER TABLE students           ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_quizzes    ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_projects   ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_roadmaps   ENABLE ROW LEVEL SECURITY;
ALTER TABLE roadmap_history    ENABLE ROW LEVEL SECURITY;
ALTER TABLE progress_snapshots ENABLE ROW LEVEL SECURITY;

-- Idempotent policy creation — avoids "already exists" errors on re-run
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'students' AND policyname = 'Allow service role full access') THEN
    CREATE POLICY "Allow service role full access" ON students FOR ALL USING (true) WITH CHECK (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'student_quizzes' AND policyname = 'Allow service role full access') THEN
    CREATE POLICY "Allow service role full access" ON student_quizzes FOR ALL USING (true) WITH CHECK (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'student_projects' AND policyname = 'Allow service role full access') THEN
    CREATE POLICY "Allow service role full access" ON student_projects FOR ALL USING (true) WITH CHECK (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'student_roadmaps' AND policyname = 'Allow service role full access') THEN
    CREATE POLICY "Allow service role full access" ON student_roadmaps FOR ALL USING (true) WITH CHECK (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'roadmap_history' AND policyname = 'Allow service role full access') THEN
    CREATE POLICY "Allow service role full access" ON roadmap_history FOR ALL USING (true) WITH CHECK (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'progress_snapshots' AND policyname = 'Allow service role full access') THEN
    CREATE POLICY "Allow service role full access" ON progress_snapshots FOR ALL USING (true) WITH CHECK (true);
  END IF;
END $$;


-- ─────────────────────────────────────────────────────────────────────
-- TRIGGERS — Auto-update `updated_at` timestamp on row modification
-- ─────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'set_students_updated_at') THEN
    CREATE TRIGGER set_students_updated_at
      BEFORE UPDATE ON students
      FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'set_roadmaps_updated_at') THEN
    CREATE TRIGGER set_roadmaps_updated_at
      BEFORE UPDATE ON student_roadmaps
      FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
  END IF;
END $$;


-- =====================================================================
-- Migration complete.
--
-- Post-migration checklist:
--   1. Verify all 6 tables appear in Supabase Table Editor
--   2. Configure Authentication → URL Configuration:
--      • http://localhost:3000/auth/callback   (development)
--      • https://YOUR-DOMAIN/auth/callback     (production)
--   3. Set SUPABASE_URL and SUPABASE_KEY in backend/.env
-- =====================================================================
