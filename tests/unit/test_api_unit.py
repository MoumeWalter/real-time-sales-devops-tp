"""Tests unitaires de l'API FastAPI.

Kafka est entièrement simulé : on vérifie la logique de l'API (routes,
validation, codes HTTP, gestion du producer), pas la connexion réelle.
"""
import json
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.main import app

VALID_PAYLOAD = {
    "customer_id": "C001",
    "product_id": "P001",
    "quantity": 2,
    "unit_price": 49.90,
}


class FakeProducer:
    """Faux KafkaProducer : mémorise les messages envoyés."""

    def __init__(self):
        self.sent = []
        self.flushed = False
        self.closed = False

    def send(self, topic, value=None):
        self.sent.append((topic, value))
        future = MagicMock()
        future.get.return_value = None
        return future

    def flush(self):
        self.flushed = True

    def close(self):
        self.closed = True


@pytest.fixture
def fake_producer(monkeypatch):
    producer = FakeProducer()
    monkeypatch.setattr(main, "create_kafka_producer", lambda: producer)
    return producer


@pytest.fixture
def client():
    return TestClient(app)


# --------------------------------------------------------------------------
# Routes simples
# --------------------------------------------------------------------------
def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "UP", "service": "sales-api"}


def test_products_list(client):
    response = client.get("/api/products")
    assert response.status_code == 200
    products = response.json()
    assert len(products) == 4
    assert {p["product_id"] for p in products} == {"P001", "P002", "P003", "P004"}


# --------------------------------------------------------------------------
# POST /api/orders
# --------------------------------------------------------------------------
def test_create_order_returns_201_and_event(client, fake_producer):
    response = client.post("/api/orders", json=VALID_PAYLOAD)
    assert response.status_code == 201

    body = response.json()
    assert body["order_id"].startswith("ORD-")
    assert body["customer_id"] == "C001"
    assert body["total_amount"] == 99.8


def test_create_order_publishes_event_to_topic(client, fake_producer):
    response = client.post("/api/orders", json=VALID_PAYLOAD)

    assert len(fake_producer.sent) == 1
    topic, value = fake_producer.sent[0]
    assert topic == main.KAFKA_TOPIC
    assert value == response.json()


def test_create_order_flushes_and_closes_producer(client, fake_producer):
    client.post("/api/orders", json=VALID_PAYLOAD)
    assert fake_producer.flushed is True
    assert fake_producer.closed is True


def test_unknown_product_returns_404_and_sends_nothing(client, fake_producer):
    payload = {**VALID_PAYLOAD, "product_id": "P999"}
    response = client.post("/api/orders", json=payload)

    assert response.status_code == 404
    assert response.json()["detail"] == "Unknown product"
    assert fake_producer.sent == []


@pytest.mark.parametrize(
    "override",
    [
        {"quantity": 0},
        {"quantity": -3},
        {"unit_price": 0},
        {"unit_price": -10},
        {"customer_id": "C"},
        {"product_id": ""},
    ],
)
def test_invalid_payload_returns_422_and_sends_nothing(client, fake_producer, override):
    response = client.post("/api/orders", json={**VALID_PAYLOAD, "customer_id": "C001", **override})

    assert response.status_code == 422
    assert fake_producer.sent == []


def test_missing_field_returns_422(client, fake_producer):
    payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "quantity"}
    response = client.post("/api/orders", json=payload)
    assert response.status_code == 422


def test_producer_is_closed_even_if_kafka_fails(monkeypatch):
    """Si Kafka échoue, l'API renvoie 500 mais ferme quand même le producer."""
    producer = FakeProducer()

    def failing_send(topic, value=None):
        future = MagicMock()
        future.get.side_effect = RuntimeError("Kafka indisponible")
        return future

    producer.send = failing_send
    monkeypatch.setattr(main, "create_kafka_producer", lambda: producer)

    failing_client = TestClient(app, raise_server_exceptions=False)
    response = failing_client.post("/api/orders", json=VALID_PAYLOAD)

    assert response.status_code == 500
    assert producer.closed is True


# --------------------------------------------------------------------------
# Configuration du producer Kafka
# --------------------------------------------------------------------------
def test_create_kafka_producer_configuration(monkeypatch):
    captured = {}

    def fake_kafka_producer(**kwargs):
        captured.update(kwargs)
        return "producer"

    monkeypatch.setattr(main, "KafkaProducer", fake_kafka_producer)

    assert main.create_kafka_producer() == "producer"
    assert captured["bootstrap_servers"] == main.KAFKA_BOOTSTRAP_SERVERS
    assert captured["retries"] == 5

    serialized = captured["value_serializer"]({"order_id": "ORD-1", "quantity": 2})
    assert isinstance(serialized, bytes)
    assert json.loads(serialized) == {"order_id": "ORD-1", "quantity": 2}
