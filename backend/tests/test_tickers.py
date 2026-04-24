def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_tickers_empty(client):
    response = client.get("/api/tickers")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["tickers"] == []


def test_create_ticker(client):
    response = client.post("/api/tickers", json={"symbol": "aapl", "name": "Apple Inc.", "sector": "Technology"})
    assert response.status_code == 201
    data = response.json()
    assert data["symbol"] == "AAPL"  # Should be uppercased
    assert data["name"] == "Apple Inc."
    assert data["id"] is not None


def test_create_duplicate_ticker(client):
    client.post("/api/tickers", json={"symbol": "MSFT", "name": "Microsoft"})
    response = client.post("/api/tickers", json={"symbol": "msft"})
    assert response.status_code == 409


def test_get_ticker(client):
    client.post("/api/tickers", json={"symbol": "NVDA", "name": "NVIDIA"})
    response = client.get("/api/tickers/NVDA")
    assert response.status_code == 200
    assert response.json()["symbol"] == "NVDA"


def test_get_ticker_not_found(client):
    response = client.get("/api/tickers/FAKE")
    assert response.status_code == 404


def test_delete_ticker(client):
    client.post("/api/tickers", json={"symbol": "TSLA"})
    response = client.delete("/api/tickers/TSLA")
    assert response.status_code == 204

    # Should be gone
    response = client.get("/api/tickers/TSLA")
    assert response.status_code == 404
