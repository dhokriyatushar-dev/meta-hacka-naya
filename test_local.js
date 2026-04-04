async function testBackend() {
  const payload = {
    name: "Test Student",
    email: "test@example.com",
    target_field: "tech",
    skills: [],
    weekly_hours: 10,
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

    console.log("Fetching student...");
    const getRes = await fetch("http://127.0.0.1:8080/api/onboarding/profile/" + payload.user_id);
    if (!getRes.ok) {
        console.log("GET FAILED", getRes.status, await getRes.text());
        return;
    }
    const getData = await getRes.json();
    console.log("GET Success:", getData.id);
  } catch (err) {
    console.error("Error:", err);
  }
}

testBackend();
