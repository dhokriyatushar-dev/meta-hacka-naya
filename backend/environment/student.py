"""
EduPath AI — Student State Management
Manages student profiles, progress tracking, and state persistence.
"""
import json
import os
import uuid
from typing import Dict, Optional, List
from environment.models import StudentProfile, Badge, BadgeType, QuizResult, SkillLevel


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)


class StudentManager:
    """Manages student profiles with JSON file persistence."""

    def __init__(self):
        self.students: Dict[str, StudentProfile] = {}
        self._load_all()

    def _filepath(self, student_id: str) -> str:
        return os.path.join(DATA_DIR, f"student_{student_id}.json")

    def _load_all(self):
        """Load all student profiles from disk."""
        if not os.path.exists(DATA_DIR):
            return
        for f in os.listdir(DATA_DIR):
            if f.startswith("student_") and f.endswith(".json"):
                try:
                    with open(os.path.join(DATA_DIR, f), "r") as fh:
                        data = json.load(fh)
                        profile = StudentProfile(**data)
                        self.students[profile.id] = profile
                except Exception:
                    pass

    def save(self, student: StudentProfile):
        """Persist student profile to disk AND sync to Supabase."""
        self.students[student.id] = student
        with open(self._filepath(student.id), "w") as f:
            json.dump(student.model_dump(), f, indent=2, default=str)

        # Sync to Supabase (non-blocking, fails gracefully)
        try:
            from db.supabase_client import upsert_student
            upsert_student(student.model_dump())
        except Exception:
            pass  # Supabase sync failure shouldn't break local operation

    def get(self, student_id: str) -> Optional[StudentProfile]:
        """Get student by ID."""
        return self.students.get(student_id)

    def create(self, name: str = "", email: str = "", student_id: str = "") -> StudentProfile:
        """Create a new student profile. Uses provided ID or generates one."""
        sid = student_id or str(uuid.uuid4())[:8]
        student = StudentProfile(
            id=sid,
            name=name,
            email=email,
        )
        self.save(student)
        return student

    def update_from_onboarding(self, student_id: str, data: dict) -> StudentProfile:
        """Update student profile from onboarding data."""
        student = self.get(student_id)
        if not student:
            student = StudentProfile(id=student_id)

        if data.get("resume_skills"):
            student.resume_skills = data["resume_skills"]
        if data.get("skills"):
            student.self_assessed_skills = [
                SkillLevel(**s) if isinstance(s, dict) else s
                for s in data["skills"]
            ]
        if data.get("target_field"):
            student.target_field = data["target_field"]
        if data.get("learning_goal"):
            student.learning_goal = data["learning_goal"]
        if data.get("job_description"):
            student.job_description = data["job_description"]
        if data.get("jd_required_skills"):
            student.jd_required_skills = data["jd_required_skills"]
        if data.get("weekly_hours"):
            student.weekly_hours = data["weekly_hours"]
        if data.get("name"):
            student.name = data["name"]
        if data.get("email"):
            student.email = data["email"]

        self.save(student)
        return student

    def complete_topic(self, student_id: str, topic_id: str) -> StudentProfile:
        """Mark a topic as completed."""
        student = self.get(student_id)
        if student and topic_id not in student.completed_topics:
            student.completed_topics.append(topic_id)
            self._check_badges(student)
            self._update_job_readiness(student)
            self.save(student)
        return student

    def record_quiz(self, student_id: str, result: QuizResult) -> StudentProfile:
        """Record a quiz result."""
        student = self.get(student_id)
        if student:
            student.quiz_history.append(result)
            if result.passed:
                student.quiz_streak += 1
                if result.topic_id not in student.completed_topics:
                    student.completed_topics.append(result.topic_id)
            else:
                student.quiz_streak = 0
            self._check_badges(student)
            self._update_job_readiness(student)
            self.save(student)

            # Sync quiz to Supabase
            try:
                from db.supabase_client import save_quiz_result
                save_quiz_result(student_id, result.model_dump())
            except Exception:
                pass
        return student

    def complete_project(self, student_id: str, project_id: str) -> StudentProfile:
        """Mark a project as completed."""
        student = self.get(student_id)
        if student and project_id not in student.completed_projects:
            student.completed_projects.append(project_id)
            self._check_badges(student)
            self._update_job_readiness(student)
            self.save(student)
        return student

    def _check_badges(self, student: StudentProfile):
        """Check and award badges based on current progress."""
        earned_ids = {b.id for b in student.badges}

        # Topic completion badges
        topic_milestones = {5: "Explorer", 10: "Scholar", 15: "Expert"}
        for count, name in topic_milestones.items():
            badge_id = f"topics_{count}"
            if len(student.completed_topics) >= count and badge_id not in earned_ids:
                student.badges.append(Badge(
                    id=badge_id, name=f"{name} Badge",
                    description=f"Completed {count} topics",
                    type=BadgeType.TOPIC_COMPLETION, icon="📚"
                ))

        # Quiz streak badges
        streak_milestones = {3: "Hat Trick", 5: "On Fire", 10: "Unstoppable"}
        for count, name in streak_milestones.items():
            badge_id = f"streak_{count}"
            if student.quiz_streak >= count and badge_id not in earned_ids:
                student.badges.append(Badge(
                    id=badge_id, name=f"{name} Streak",
                    description=f"Passed {count} quizzes in a row",
                    type=BadgeType.QUIZ_STREAK, icon="🔥"
                ))

        # Project badges
        project_milestones = {1: "Builder", 3: "Creator", 5: "Architect"}
        for count, name in project_milestones.items():
            badge_id = f"projects_{count}"
            if len(student.completed_projects) >= count and badge_id not in earned_ids:
                student.badges.append(Badge(
                    id=badge_id, name=f"{name} Badge",
                    description=f"Completed {count} projects",
                    type=BadgeType.PROJECT_SUCCESS, icon="🛠️"
                ))

        # Job ready badge
        if student.job_readiness_score >= 0.8 and "job_ready" not in earned_ids:
            student.badges.append(Badge(
                id="job_ready", name="Job Ready!",
                description="Achieved 80%+ job readiness score",
                type=BadgeType.JOB_READY, icon="💼"
            ))

    def _update_job_readiness(self, student: StudentProfile):
        """Calculate job readiness score based on progress."""
        score = 0.0
        total_weight = 0.0

        # Topics completed (40% weight)
        if student.jd_required_skills:
            all_skills = set(student.jd_required_skills)
            matched = sum(1 for t in student.completed_topics
                          if any(s.lower() in t.lower() for s in all_skills))
            topic_score = matched / max(len(all_skills), 1)
        else:
            topic_score = len(student.completed_topics) / 15.0
        score += min(topic_score, 1.0) * 0.4
        total_weight += 0.4

        # Quiz performance (30% weight)
        if student.quiz_history:
            avg_score = sum(q.score for q in student.quiz_history) / len(student.quiz_history)
            score += (avg_score / 100.0) * 0.3
        total_weight += 0.3

        # Projects completed (30% weight)
        project_score = len(student.completed_projects) / 5.0
        score += min(project_score, 1.0) * 0.3
        total_weight += 0.3

        student.job_readiness_score = round(score / total_weight, 2) if total_weight > 0 else 0.0

    def get_skill_levels(self, student_id: str) -> Dict[str, float]:
        """Get computed skill levels for a student."""
        student = self.get(student_id)
        if not student:
            return {}

        levels = {}
        # From self-assessed skills
        for s in student.self_assessed_skills:
            levels[s.skill] = s.proficiency

        # From completed topics (boost)
        for topic_id in student.completed_topics:
            levels[topic_id] = min(levels.get(topic_id, 0) + 0.3, 1.0)

        # From quiz scores
        for q in student.quiz_history:
            levels[q.topic_id] = max(levels.get(q.topic_id, 0), q.score / 100.0)

        return levels

    def record_link_click(self, student_id: str, topic_id: str, url: str) -> bool:
        """
        Records that student clicked a resource link.
        Returns True if this is their first click for this topic (unlock event).
        """
        student = self.get(student_id)
        if not student:
            return False

        is_first = topic_id not in student.clicked_resource_links or \
                   len(student.clicked_resource_links.get(topic_id, [])) == 0

        if topic_id not in student.clicked_resource_links:
            student.clicked_resource_links[topic_id] = []

        if url not in student.clicked_resource_links[topic_id]:
            student.clicked_resource_links[topic_id].append(url)

        self.save(student)
        return is_first

    def mark_topic_studied(self, student_id: str, topic_id: str) -> bool:
        """
        Called when student clicks Mark as Complete.
        Only works if student has at least 1 clicked link for this topic.
        Returns False if no link was clicked (guard).
        Returns True and adds to topics_studied if valid.
        """
        student = self.get(student_id)
        if not student:
            return False

        # Guard: must have clicked at least one link
        if topic_id not in student.clicked_resource_links or \
           len(student.clicked_resource_links[topic_id]) == 0:
            return False

        if topic_id not in student.topics_studied:
            student.topics_studied.append(topic_id)

        self.save(student)
        return True


# Global instance
student_manager = StudentManager()
