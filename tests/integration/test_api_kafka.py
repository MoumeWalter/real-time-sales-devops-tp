"""Test d'intégration A : API -> Kafka.

Utilise l'API et Kafka réellement démarrés (docker compose). Rien n'est simulé.
Activé avec RUN_INTEGRATION_TESTS=true.
"""
import os
import uuid

import pytest
import requests

from tests.helpers import (
    API_URL,
    find_kafka_message,
    kafka_total_offset,
    make_consumer,
)

RUN_INTEGRATION = os.getenv("RUN_INTEGRATION_TESTS", "false").lower() == "true"

pytestmark = pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="Integration tests disabled. Set RUN_INTEGRATION_TESTS=true.",
)


def valid_payload(**overrides):
    payload = {
        # identifiant client unique : permet de repérer les données de ce test
        "customer_id": f"IT{uuid.uuid4().hex[:6].upper()}",
        "product_id": "P001",
        "quantity": 2,
        "unit_price": 50.0,
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def consumer():
    kafka_consumer = make_consumer()
    yield kafka_consumer
    kafka_consumer.close()


def test_api_is_reachable():
    response = requests.get(f"{API_URL}/api/health", timeout=5)
    assert response.status_code == 200
    assert response.json()["status"] == "UP"


def test_order_is_published_to_kafka(consumer):
    payload = valid_payload()

    response = requests.post(f"{API_URL}/api/orders", json=payload, timeout=15)
    assert response.status_code == 201
    body = response.json()

    message = find_kafka_message(consumer, body["order_id"], timeout=30)

    # L'événement lu dans Kafka est exactement celui renvoyé par l'API.
    assert message == body
    assert message["customer_id"] == payload["customer_id"]
    assert message["total_amount"] == 100.0


def test_rejected_orders_are_not_published(consumer):
    offset_before = kafka_total_offset(consumer)

    invalid_quantity = requests.post(
        f"{API_URL}/api/orders", json=valid_payload(quantity=0), timeout=15
    )
    unknown_product = requests.post(
        f"{API_URL}/api/orders", json=valid_payload(product_id="P999"), timeout=15
    )

    assert invalid_quantity.status_code == 422
    assert unknown_product.status_code == 404
    # Aucun message supplémentaire n'a été écrit dans le topic.
    assert kafka_total_offset(consumer) == offset_before
