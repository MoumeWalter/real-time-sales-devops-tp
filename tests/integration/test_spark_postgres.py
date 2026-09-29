"""Test d'intégration B : Kafka -> Spark -> PostgreSQL.

On publie directement dans Kafka (sans passer par l'API) et on vérifie que
Spark Streaming a traité l'événement et l'a écrit dans processed_orders.
Activé avec RUN_INTEGRATION_TESTS=true.

Attention : order_id est la clé primaire de processed_orders. Ne jamais
publier deux fois le même order_id, sinon l'écriture JDBC échoue et le job
Spark s'arrête.
"""
import os
from datetime import datetime
from decimal import Decimal

import pytest

from tests.helpers import (
    PIPELINE_TIMEOUT,
    fetch_order,
    make_event,
    new_order_id,
    publish_event,
    wait_until,
)

RUN_INTEGRATION = os.getenv("RUN_INTEGRATION_TESTS", "false").lower() == "true"

pytestmark = pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="Integration tests disabled. Set RUN_INTEGRATION_TESTS=true.",
)


def wait_for_order(order_id):
    return wait_until(
        lambda: fetch_order(order_id),
        timeout=PIPELINE_TIMEOUT,
        interval=2,
        description=f"la commande {order_id} dans processed_orders "
                    "(Spark Streaming est-il démarré ?)",
    )


def test_valid_event_is_stored_in_postgres(order_cleanup):
    order_id = new_order_id()
    order_cleanup.append(order_id)

    event = make_event(order_id, customer_id="C-SPARK", quantity=3, unit_price=100.0)
    publish_event(event)

    row = wait_for_order(order_id)

    assert row["customer_id"] == "C-SPARK"
    assert row["product_id"] == "P001"
    assert row["quantity"] == 3
    assert row["unit_price"] == Decimal("100.00")
    assert row["total_amount"] == Decimal("300.00")
    assert isinstance(row["event_timestamp"], datetime)
    assert row["processed_at"] is not None


def test_invalid_event_is_filtered_by_spark(order_cleanup):
    """Spark ignore les événements avec quantité <= 0 (filtre du job)."""
    invalid_id = new_order_id("ORD-BAD")
    sentinel_id = new_order_id("ORD-OK")
    order_cleanup.extend([invalid_id, sentinel_id])

    # Même topic, même partition : l'ordre d'arrivée est garanti.
    publish_event(make_event(invalid_id, quantity=0))
    publish_event(make_event(sentinel_id, quantity=1, unit_price=10.0))

    # Quand la sentinelle est en base, l'événement invalide a déjà été traité.
    wait_for_order(sentinel_id)

    assert fetch_order(invalid_id) is None
