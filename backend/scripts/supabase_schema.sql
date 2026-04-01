-- ============================================
-- EduPath AI — Supabase Database Schema
-- Run this in Supabase SQL Editor
-- ============================================

-- 1. Students Profile Table
CREATE TABLE IF NOT EXISTS students (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  name TEXT DEFAULT '',
  email TEXT DEFAULT '',
  target_field TEXT DEFAULT 'tech',
  learning_goal TEXT DEFAULT '',
  job_description TEXT DEFAULT '',
  weekly_hours INT DEFAULT 10,
  job_readiness_score FLOAT DEFAULT 0.0,
  quiz_streak INT DEFAULT 0,
  resume_skills JSONB DEFAULT '[]'::jsonb,
  self_assessed_skills JSONB DEFAULT '[]'::jsonb,
  jd_required_skills JSONB DEFAULT '[]'::jsonb,
  completed_topics JSONB DEFAULT '[]'::jsonb,
  completed_projects JSONB DEFAULT '[]'::jsonb,
  topics_studied JSONB DEFAULT '[]'::jsonb,
  clicked_resource_links JSONB DEFAULT '{}'::jsonb,
  badges JSONB DEFAULT '[]'::jsonb,
  onboarding_complete BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Quiz History Table
CREATE TABLE IF NOT EXISTS student_quizzes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id UUID REFERENCES students(id) ON DELETE CASCADE,
  topic_id TEXT NOT NULL,
  score FLOAT NOT NULL DEFAULT 0,
  total_questions INT DEFAULT 0,
  correct_answers INT DEFAULT 0,
  passed BOOLEAN DEFAULT FALSE,
  difficulty TEXT DEFAULT 'medium',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Project Evaluations Table
CREATE TABLE IF NOT EXISTS student_projects (
  id TEXT PRIMARY KEY,
  student_id UUID REFERENCES students(id) ON DELETE CASCADE,
  project_title TEXT NOT NULL,
  project_type TEXT DEFAULT 'mini_project',
  submission_text TEXT DEFAULT '',
  score FLOAT DEFAULT 0,
  grade TEXT DEFAULT 'N/A',
  is_passing BOOLEAN DEFAULT FALSE,
  evaluation_data JSONB DEFAULT '{}'::jsonb,
  submitted_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Roadmap Cache Table
CREATE TABLE IF NOT EXISTS student_roadmaps (
  student_id UUID PRIMARY KEY REFERENCES students(id) ON DELETE CASCADE,
  roadmap_data JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_quizzes_student ON student_quizzes(student_id);
CREATE INDEX IF NOT EXISTS idx_projects_student ON student_projects(student_id);

-- 6. Disable RLS for backend access (using service role or anon key with no policies)
ALTER TABLE students ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_quizzes ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_roadmaps ENABLE ROW LEVEL SECURITY;

-- 7. RLS Policies — Users can only access their own data
CREATE POLICY "Users read own data" ON students FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users update own data" ON students FOR UPDATE USING (auth.uid() = id);
CREATE POLICY "Users insert own data" ON students FOR INSERT WITH CHECK (auth.uid() = id);

CREATE POLICY "Users read own quizzes" ON student_quizzes FOR SELECT USING (auth.uid() = student_id);
CREATE POLICY "Users insert own quizzes" ON student_quizzes FOR INSERT WITH CHECK (auth.uid() = student_id);

CREATE POLICY "Users read own projects" ON student_projects FOR SELECT USING (auth.uid() = student_id);
CREATE POLICY "Users insert own projects" ON student_projects FOR INSERT WITH CHECK (auth.uid() = student_id);

CREATE POLICY "Users read own roadmap" ON student_roadmaps FOR SELECT USING (auth.uid() = student_id);
CREATE POLICY "Users manage own roadmap" ON student_roadmaps FOR ALL USING (auth.uid() = student_id);

-- 8. Auto-update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER students_updated_at
  BEFORE UPDATE ON students
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER roadmaps_updated_at
  BEFORE UPDATE ON student_roadmaps
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- 9. Function to auto-create student profile on signup
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO students (id, email, name)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.raw_user_meta_data->>'name', '')
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger: auto-create student on auth signup
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_user();
