def test_health_returns_ok(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["environment"] in {"development", "staging", "production"}
    assert body["database_mode"] in {"json", "postgres"}
    assert body["ai_provider"] in {"ollama", "openai", "azure_openai"}
