def test_not_found_uses_standard_format(client):
    res = client.get("/api/v1/tidak-ada")
    assert res.status_code == 404
    body = res.json()
    assert body["success"] is False
    assert body["error"]["code"] == "NOT_FOUND"
    assert "message" in body["error"]
