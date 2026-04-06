-- =====================================================
-- EduPath AI — Complete Supabase Database Schema
-- Copy & paste this ENTIRE file into the Supabase
-- SQL Editor and hit "Run".
-- Safe to run multiple times (uses IF NOT EXISTS).
-- =====================================================


-- ═══════════════════════════════════════════════════════
-- 1. STUDENTS — Core student profiles
-- ═══════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS students (
  id TEXT PRIMARY KEY,                              -- Supabase auth user UUID (as text)
  name TEXT NOT NULL DEFAULT '',
  email TEXT DEFAULT '',
  target_field TEXT DEFAULT 'tech',                  -- e.g. 'ai_ml', 'web_dev', 'data_science'
  learning_goal TEXT DEFAULT '',
  job_description TEXT DEFAULT '',
  weekly_hours INT DEFAULT 10,
  job_readiness_score FLOAT DEFAULT 0.0,
  quiz_streak INT DEFAULT 0,

  -- JSON-encoded arrays/objects (stored as TEXT for flexibility)
  resume_skills TEXT DEFAULT '[]',                   -- parsed resume skills
  self_assessed_skills TEXT DEFAULT '[]',            -- [{skill, level, proficiency}]
  jd_required_skills TEXT DEFAULT '[]',              -- skills from job description
  completed_topics TEXT DEFAULT '[]',                -- topic IDs completed
  completed_projects TEXT DEFAULT '[]',              -- project IDs completed
  topics_studied TEXT DEFAULT '[]',                  -- topics the student has clicked resources for
  clicked_resource_links TEXT DEFAULT '{}',          -- {topic_id: [url, url, ...]}
  badges TEXT DEFAULT '[]',                          -- badge objects [{name, icon, earned, ...}]
  mastery_probabilities TEXT DEFAULT '{}',           -- {topic_id: probability}

  onboarding_complete BOOLEAN DEFAULT FALSE,

  -- Tracking columns (for profile feature)
  current_roadmap_id UUID,
  total_roadmaps_completed INT DEFAULT 0,

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);


-- ═══════════════════════════════════════════════════════
-- 2. STUDENT_QUIZZES — Quiz attempt history
-- ═══════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS student_quizzes (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  student_id TEXT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  topic_id TEXT NOT NULL DEFAULT '',
  score INT DEFAULT 0,                              -- percentage 0-100
  total_questions INT DEFAULT 0,
  correct_answers INT DEFAULT 0,
  passed BOOLEAN DEFAULT FALSE,
  difficulty TEXT DEFAULT 'medium',                  -- easy, medium, hard
  created_at TIMESTAMPTZ DEFAULT now()
);


-- ═══════════════════════════════════════════════════════
-- 3. STUDENT_PROJECTS — Project submissions & evaluations
-- ═══════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS student_projects (
  id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  student_id TEXT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  project_title TEXT DEFAULT '',
  project_type TEXT DEFAULT 'mini_project',          -- mini_project, capstone
  submission_text TEXT DEFAULT '',
  score INT DEFAULT 0,                              -- AI evaluation score 0-100
  grade TEXT DEFAULT 'N/A',                          -- A+, A, B+, B, etc.
  is_passing BOOLEAN DEFAULT FALSE,
  evaluation_data TEXT DEFAULT '{}',                 -- full AI evaluation JSON
  created_at TIMESTAMPTZ DEFAULT now()
);


-- ═══════════════════════════════════════════════════════
-- 4. STUDENT_ROADMAPS — Current active roadmap per student
-- ═══════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS student_roadmaps (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  student_id TEXT NOT NULL UNIQUE,                   -- one active roadmap per student
  roadmap_data TEXT DEFAULT '{}',                    -- full roadmap JSON
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);


-- ═══════════════════════════════════════════════════════
-- 5. ROADMAP_HISTORY — Archived past roadmaps
--    (when user quits or switches roadmap)
-- ═══════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS roadmap_history (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  student_id TEXT NOT NULL,
  roadmap_data JSONB NOT NULL,                       -- full roadmap JSON snapshot
  topics_covered TEXT[] DEFAULT '{}',                -- array of topic IDs covered
  started_at TIMESTAMPTZ DEFAULT now(),
  archived_at TIMESTAMPTZ DEFAULT now(),
  completion_percentage FLOAT DEFAULT 0.0            -- 0.0 to 100.0
);


-- ═══════════════════════════════════════════════════════
-- 6. PROGRESS_SNAPSHOTS — Periodic progress check-ins
--    (for tracking improvement over time)
-- ═══════════════════════════════════════════════════════
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


-- ═══════════════════════════════════════════════════════
-- INDEXES — for query performance
-- ═══════════════════════════════════════════════════════
CREATE INDEX IF NOT EXISTS idx_quizzes_student       ON student_quizzes(student_id);
CREATE INDEX IF NOT EXISTS idx_quizzes_topic          ON student_quizzes(topic_id);
CREATE INDEX IF NOT EXISTS idx_quizzes_created        ON student_quizzes(created_at);
CREATE INDEX IF NOT EXISTS idx_projects_student       ON student_projects(student_id);
CREATE INDEX IF NOT EXISTS idx_roadmaps_student       ON student_roadmaps(student_id);
CREATE INDEX IF NOT EXISTS idx_roadmap_history_student ON roadmap_history(student_id);
CREATE INDEX IF NOT EXISTS idx_progress_student       ON progress_snapshots(student_id);
CREATE INDEX IF NOT EXISTS idx_progress_date          ON progress_snapshots(snapshot_date);


-- ═══════════════════════════════════════════════════════
-- ROW LEVEL SECURITY (RLS)
-- ═══════════════════════════════════════════════════════
ALTER TABLE students           ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_quizzes    ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_projects   ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_roadmaps   ENABLE ROW LEVEL SECURITY;
ALTER TABLE roadmap_history    ENABLE ROW LEVEL SECURITY;
ALTER TABLE progress_snapshots ENABLE ROW LEVEL SECURITY;

-- Allow full access via service role key (used by backend)
-- Drop existing policies first to avoid "already exists" errors
DO $$
BEGIN
  -- students
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'students' AND policyname = 'Allow service role full access') THEN
    CREATE POLICY "Allow service role full access" ON students FOR ALL USING (true) WITH CHECK (true);
  END IF;
  -- student_quizzes
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'student_quizzes' AND policyname = 'Allow service role full access') THEN
    CREATE POLICY "Allow service role full access" ON student_quizzes FOR ALL USING (true) WITH CHECK (true);
  END IF;
  -- student_projects
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'student_projects' AND policyname = 'Allow service role full access') THEN
    CREATE POLICY "Allow service role full access" ON student_projects FOR ALL USING (true) WITH CHECK (true);
  END IF;
  -- student_roadmaps
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'student_roadmaps' AND policyname = 'Allow service role full access') THEN
    CREATE POLICY "Allow service role full access" ON student_roadmaps FOR ALL USING (true) WITH CHECK (true);
  END IF;
  -- roadmap_history
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'roadmap_history' AND policyname = 'Allow service role full access') THEN
    CREATE POLICY "Allow service role full access" ON roadmap_history FOR ALL USING (true) WITH CHECK (true);
  END IF;
  -- progress_snapshots
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'progress_snapshots' AND policyname = 'Allow service role full access') THEN
    CREATE POLICY "Allow service role full access" ON progress_snapshots FOR ALL USING (true) WITH CHECK (true);
  END IF;
END $$;


-- ═══════════════════════════════════════════════════════
-- AUTO-UPDATE updated_at TRIGGER
-- ═══════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to tables with updated_at
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


-- ═══════════════════════════════════════════════════════
-- DONE!
-- ═══════════════════════════════════════════════════════
-- Tables created:
--   1. students              — core student profiles
--   2. student_quizzes       — quiz attempt history
--   3. student_projects      — project submissions
--   4. student_roadmaps      — current active roadmap
--   5. roadmap_history       — archived past roadmaps
--   6. progress_snapshots    — periodic progress tracking
--
-- IMPORTANT: Also configure Supabase Auth:
--   1. Go to Authentication → URL Configuration
--   2. Add these Redirect URLs:
--      • http://localhost:3000/auth/callback
--      • https://YOUR-PRODUCTION-URL/auth/callback
-- ═══════════════════════════════════════════════════════
