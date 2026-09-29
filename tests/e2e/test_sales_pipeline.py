"""Test End-to-End : API -> Kafka -> PySpark -> PostgreSQL.

Given  l'infrastructure est démarrée,
When   une commande (C100, P001, 3 x 100) est envoyée à l'API,
Then   elle est publiée dans Kafka, traitée par Spark et enregistrée dans
       PostgreSQL avec un montant total de 300.

Aucun time.sleep arbitraire : on interroge PostgreSQL (polling) jusqu'à
obtenir le résultat, avec un timeout explicite.
Activé avec RUN_E2E_TESTS=true.
"""
import os
from datetime import datetime
from decimal import Decimal

import pytest
import requests

from tests.helpers import (
    API_URL,
    PIPELINE_TIMEOUT,
    fetch_order,
    find_kafka_message,
    make_consumer,
    wait_until,
)

RUN_E2E = os.getenv("RUN_E2E_TESTS", "false").lower() == "true"

pytestmark = pytest.mark.skipif(
    not RUN_E2E,
    reason="E2E tests disabled. Set RUN_E2E_TESTS=true.",
)


def test_order_flows_through_the_whole_pipeline(order_cleanup):
    # ---- Given : l'API répond ------------------------------------------------
    health = requests.get(f"{API_URL}/api/health", timeout=5)
    assert health.status_code == 200

    # ---- When : une commande est envoyée à l'API -----------------------------
    payload = {
        "customer_id": "C100",
        "product_id": "P001",
        "quantity": 3,
        "unit_price": 100,
    }
    response = requests.post(f"{API_URL}/api/orders", json=payload, timeout=15)
    assert response.status_code == 201
    event = response.json()
    order_id = event["order_id"]
    order_cleanup.append(order_id)
    assert event["total_amount"] == 300

    # ---- Then 1 : l'événement est publié dans Kafka ---------------------------
    consumer = make_consumer()
    try:
        message = find_kafka_message(consumer, order_id, timeout=30)
    finally:
        consumer.close()
    assert message == event

    # ---- Then 2 : Spark le traite et l'écrit dans PostgreSQL (polling) --------
    row = wait_until(
        lambda: fetch_order(order_id),
        timeout=PIPELINE_TIMEOUT,
        interval=2,
        description=f"la commande {order_id} dans processed_orders "
                    f"(délai max {PIPELINE_TIMEOUT:.0f}s)",
    )

    # ---- Then 3 : les valeurs sont celles attendues ---------------------------
    assert row["customer_id"] == "C100"
    assert row["product_id"] == "P001"
    assert row["quantity"] == 3
    assert row["unit_price"] == Decimal("100.00")
    assert row["total_amount"] == Decimal("300.00")

    sent_at = datetime.fromisoformat(event["timestamp"])
    assert abs((row["event_timestamp"] - sent_at).total_seconds()) < 1
    assert row["processed_at"] is not None
