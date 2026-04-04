"""
EduPath AI — Student Difficulty Model (Upgrade 2)
Realistic student learning simulation where quiz scores depend on
teaching quality, prerequisite completion, and skill growth.
"""
import random
from typing import Dict, List, Optional
from environment.curriculum import TOPIC_GRAPH


class StudentDifficultyModel:
    """
    Models realistic student learning where quiz outcomes depend on:
    - Student's current skill level for the topic
    - Completion of prerequisites (order bonus)
    - Topic difficulty
    - Accumulated learning (skill growth over time)
    """

    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)
        self.skill_levels: Dict[str, float] = {}  # topic_id -> 0.0-1.0

    def reset(self, seed: int = 42):
        """Reset the model for a new episode."""
        self._rng = random.Random(seed)
        self.skill_levels = {}

    def initialize_from_profile(self, self_assessed_skills: list, resume_skills: list):
        """Initialize skill levels from student's onboarding data."""
        for skill in self_assessed_skills:
            skill_name = skill.skill if hasattr(skill, 'skill') else skill.get('skill', '')
            proficiency = skill.proficiency if hasattr(skill, 'proficiency') else skill.get('proficiency', 0.0)
            # Map skill names to topic IDs where possible
            skill_lower = skill_name.lower().replace(' ', '_')
            self.skill_levels[skill_lower] = proficiency
            # Also check for matching topic IDs
            for topic_id in TOPIC_GRAPH:
                if skill_lower in topic_id or topic_id in skill_lower:
                    self.skill_levels[topic_id] = max(
                        self.skill_levels.get(topic_id, 0.0), proficiency
                    )

        # Resume skills give a small base
        for rs in resume_skills:
            rs_lower = rs.lower().replace(' ', '_')
            for topic_id in TOPIC_GRAPH:
                if rs_lower in topic_id or topic_id in rs_lower:
                    self.skill_levels[topic_id] = max(
                        self.skill_levels.get(topic_id, 0.0), 0.2
                    )

    def simulate_quiz_score(
        self,
        topic_id: str,
        completed_topics: List[str],
    ) -> int:
        """
        Simulate a realistic quiz score based on the student difficulty model.

        quiz_score = base_score × skill_multiplier × difficulty_penalty + order_bonus + noise
        
        Calibrated to match original env behavior (~60-85 for studied topics)
        while rewarding proper prereq ordering and teaching quality.
        """
        topic = TOPIC_GRAPH.get(topic_id)
        if not topic:
            return self._rng.randint(40, 70)

        # Base score: floor 50, scales with skill to 100
        skill = self.skill_levels.get(topic_id, 0.3)
        base_score = 50 + (skill * 50)  # 50-100 range

        # Skill multiplier: boost from completed prerequisite skills
        prereq_skills = []
        for prereq_id in topic.prerequisites:
            prereq_skills.append(self.skill_levels.get(prereq_id, 0.0))
        avg_prereq_skill = sum(prereq_skills) / max(len(prereq_skills), 1) if prereq_skills else 0.0
        skill_multiplier = 1.0 + (avg_prereq_skill * 0.3)

        # Difficulty penalty: gentle — difficulty 1-5 → 0.96-0.80
        difficulty_penalty = 1.0 - (topic.difficulty * 0.04)

        # Order bonus: +15 if all prereqs completed in correct order
        order_bonus = 0
        all_prereqs_met = all(p in completed_topics for p in topic.prerequisites)
        if all_prereqs_met and len(topic.prerequisites) > 0:
            order_bonus = 15

        # Calculate raw score
        raw_score = base_score * skill_multiplier * difficulty_penalty + order_bonus

        # Gaussian noise ±8 points
        noise = self._rng.gauss(0, 8)
        final_score = raw_score + noise

        # Clamp to [0, 100]
        return int(max(0, min(100, final_score)))

    def update_skill_after_quiz(self, topic_id: str, passed: bool):
        """Update skill levels after a quiz attempt."""
        if passed:
            current = self.skill_levels.get(topic_id, 0.3)
            self.skill_levels[topic_id] = min(current + 0.3, 1.0)
        else:
            # Small improvement even on failure (learning from mistakes)
            current = self.skill_levels.get(topic_id, 0.3)
            self.skill_levels[topic_id] = min(current + 0.05, 1.0)

    def update_skill_after_project(self, related_topic_ids: List[str]):
        """Update skill levels after completing a mini project."""
        for topic_id in related_topic_ids:
            current = self.skill_levels.get(topic_id, 0.3)
            self.skill_levels[topic_id] = min(current + 0.1, 1.0)

    def update_skill_after_capstone(self, field: str):
        """Update skill levels after completing a capstone project."""
        for topic_id, topic in TOPIC_GRAPH.items():
            if topic.field == field:
                current = self.skill_levels.get(topic_id, 0.0)
                self.skill_levels[topic_id] = min(current + 0.2, 1.0)

    def update_skill_after_topic_study(self, topic_id: str):
        """Update skill when a topic is recommended/studied."""
        current = self.skill_levels.get(topic_id, 0.0)
        self.skill_levels[topic_id] = min(current + 0.25, 1.0)

    def get_skill(self, topic_id: str) -> float:
        """Get current skill level for a topic."""
        return self.skill_levels.get(topic_id, 0.3)

    def get_all_skills(self) -> Dict[str, float]:
        """Get all skill levels."""
        return dict(self.skill_levels)
