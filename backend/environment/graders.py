"""
EduPath AI — Task Graders
Deterministic graders for Task 1 (Easy), Task 2 (Medium), Task 3 (Hard).
Each grader scores 0.0 to 1.0.
Graders accept a StudentProfile and evaluate the final state.
"""
from typing import List, Dict, Optional
from environment.models import StudentProfile
from environment.curriculum import TOPIC_GRAPH


def grade_task1(student: StudentProfile) -> float:
    """
    Task 1 (Easy): Complete beginner wants to learn Python from scratch.
    Agent must sequence 5 topics correctly, respecting all prerequisites.
    Grader: % of expected topics completed (0.0 – 1.0)
    """
    expected = [
        "python_basics",
        "python_control_flow",
        "python_oop",
        "data_structures",
        "version_control",
    ]

    if not student.completed_topics:
        return 0.0

    # Score: how many expected topics were completed
    correct = sum(1 for t in expected if t in student.completed_topics)

    # Bonus: check prerequisite ordering was respected in completion order
    order_bonus = 0.0
    completed_set = set()
    for topic_id in student.completed_topics:
        topic = TOPIC_GRAPH.get(topic_id)
        if topic and topic_id in expected:
            prereqs_met = all(p in completed_set for p in topic.prerequisites)
            if prereqs_met:
                order_bonus += 0.1
        completed_set.add(topic_id)

    score = (correct / len(expected)) * 0.7 + min(order_bonus, 0.3)
    return round(min(score, 1.0), 4)


def grade_task2(student: StudentProfile) -> float:
    """
    Task 2 (Medium): Knows Python basics, goal = Data Analyst job in 3 months.
    Grader: Topic coverage (50%) + quiz performance (50%).
    """
    data_analyst_topics = [
        "statistics", "data_analysis", "data_visualization",
        "databases", "machine_learning"
    ]

    # 1. Topic coverage (50%): how many DA topics completed
    covered = sum(1 for t in data_analyst_topics if t in student.completed_topics)
    coverage_score = covered / len(data_analyst_topics)

    # 2. Quiz performance (50%): average quiz score and adaptation
    quiz_score = 0.0
    if student.quiz_history:
        avg = sum(q.score for q in student.quiz_history) / len(student.quiz_history)
        quiz_score = avg / 100.0

        # Bonus for retries (adaptation evidence)
        topics_quizzed = {}
        for q in student.quiz_history:
            topics_quizzed[q.topic_id] = topics_quizzed.get(q.topic_id, 0) + 1
        retried = sum(1 for count in topics_quizzed.values() if count > 1)
        if retried > 0:
            quiz_score = min(quiz_score + 0.1, 1.0)

    final = (coverage_score * 0.5) + (quiz_score * 0.5)
    return round(min(final, 1.0), 4)


def grade_task3(student: StudentProfile) -> float:
    """
    Task 3 (Hard): Doctor learning AI for healthcare (cross-domain).
    Grader: Job readiness (40%) + topic efficiency (30%) + cross-domain bridging (30%).
    """
    jd_skills = [
        "python", "machine_learning", "deep_learning",
        "medical_imaging", "clinical_data", "nlp"
    ]

    # 1. Job readiness (40%): JD skills covered via completed topics
    jd_covered = 0
    for skill in jd_skills:
        for topic in student.completed_topics:
            if skill.lower().replace("_", " ") in topic.lower().replace("_", " "):
                jd_covered += 1
                break
    job_readiness = jd_covered / max(len(jd_skills), 1)

    # 2. Topic efficiency (30%): more completed topics = better
    topic_count = len(student.completed_topics)
    efficiency = min(topic_count / 8.0, 1.0)  # 8 topics is good pace

    # 3. Cross-domain bridging (30%): both tech and healthcare topics?
    tech_completed = [t for t in student.completed_topics if TOPIC_GRAPH.get(t) and TOPIC_GRAPH[t].field == "tech"]
    domain_completed = [t for t in student.completed_topics if TOPIC_GRAPH.get(t) and TOPIC_GRAPH[t].field == "healthcare"]

    cross_domain = 0.0
    if tech_completed and domain_completed:
        balance = min(len(tech_completed), len(domain_completed)) / max(len(tech_completed), len(domain_completed))
        cross_domain = balance
    elif tech_completed or domain_completed:
        cross_domain = 0.3

    final = (job_readiness * 0.4) + (efficiency * 0.3) + (cross_domain * 0.3)
    return round(min(final, 1.0), 4)
