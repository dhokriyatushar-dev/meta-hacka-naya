async function testBackend() {
  const payload = {
    name: "Test Student",
    email: "test@example.com",
    target_field: "tech",
    skills: [{ skill: "Python", level: "Beginner", proficiency: 0.2 }],
    weekly_hours: 10,
    job_description: "Looking for a seasoned Python developer with React experience.",
    resume_text: "I am a web developer with 3 years of react and python.",
    learning_goal: "testing",
    user_id: "test-uuid-123456"
  };

  try {
    console.log("Adding student...");
    const res = await fetch("http://127.0.0.1:8080/api/onboarding/complete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    
    if (!res.ok) {
        console.log("POST FAILED", res.status, await res.text());
        return;
    }
    const data = await res.json();
    console.log("POST Success:", data);
  } catch (err) {
    console.error("Error:", err);
  }
}

testBackend();
