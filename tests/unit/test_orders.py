"""Tests unitaires des règles métier : modèle Order et build_order_event.

Aucun service externe (Kafka, Spark, PostgreSQL) n'est nécessaire.
"""
import re
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.main import Order, OrderEvent, build_order_event


def make_order(**overrides) -> Order:
    """Construit une commande valide, avec possibilité de surcharger un champ."""
    data = {
        "customer_id": "C001",
        "product_id": "P001",
        "quantity": 2,
        "unit_price": 50.0,
    }
    data.update(overrides)
    return Order(**data)


# --------------------------------------------------------------------------
# Calcul du montant total
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "quantity, unit_price, expected",
    [
        (2, 50.0, 100.0),
        (3, 100, 300.0),          # scénario E2E du TP
        (2, 49.90, 99.8),
        (1, 0.01, 0.01),
        (3, 0.1, 0.3),            # piège flottant : 3 * 0.1 = 0.30000000000000004
        (3, 19.99, 59.97),
        (1000, 100000, 100000000.0),
    ],
)
def test_total_amount(quantity, unit_price, expected):
    event = build_order_event(make_order(quantity=quantity, unit_price=unit_price))
    assert event["total_amount"] == expected


def test_total_amount_is_rounded_to_two_decimals():
    event = build_order_event(make_order(quantity=3, unit_price=33.333))
    assert event["total_amount"] == round(3 * 33.333, 2)


# --------------------------------------------------------------------------
# Quantité
# --------------------------------------------------------------------------
@pytest.mark.parametrize("quantity", [1, 2, 999, 1000])
def test_quantity_valid(quantity):
    assert make_order(quantity=quantity).quantity == quantity


@pytest.mark.parametrize("quantity", [0, -1, -100, 1001])
def test_quantity_invalid(quantity):
    with pytest.raises(ValidationError):
        make_order(quantity=quantity)


def test_quantity_zero_is_rejected():
    with pytest.raises(ValidationError):
        make_order(quantity=0)


def test_quantity_negative_is_rejected():
    with pytest.raises(ValidationError):
        make_order(quantity=-5)


def test_quantity_must_be_integer():
    with pytest.raises(ValidationError):
        make_order(quantity="beaucoup")


# --------------------------------------------------------------------------
# Prix unitaire
# --------------------------------------------------------------------------
@pytest.mark.parametrize("price", [0.01, 1, 49.90, 100000])
def test_unit_price_valid(price):
    assert make_order(unit_price=price).unit_price == price


@pytest.mark.parametrize("price", [0, -0.01, -50, 100000.01])
def test_unit_price_invalid(price):
    with pytest.raises(ValidationError):
        make_order(unit_price=price)


def test_unit_price_must_be_numeric():
    with pytest.raises(ValidationError):
        make_order(unit_price="gratuit")


# --------------------------------------------------------------------------
# Identifiants client et produit
# --------------------------------------------------------------------------
@pytest.mark.parametrize("customer_id", ["C1", "C001", "CUSTOMER-123"])
def test_customer_id_valid(customer_id):
    assert make_order(customer_id=customer_id).customer_id == customer_id


@pytest.mark.parametrize("customer_id", ["", "C"])
def test_customer_id_too_short(customer_id):
    with pytest.raises(ValidationError):
        make_order(customer_id=customer_id)


@pytest.mark.parametrize("product_id", ["P1", "P001"])
def test_product_id_valid(product_id):
    assert make_order(product_id=product_id).product_id == product_id


@pytest.mark.parametrize("product_id", ["", "P"])
def test_product_id_too_short(product_id):
    with pytest.raises(ValidationError):
        make_order(product_id=product_id)


@pytest.mark.parametrize(
    "missing", ["customer_id", "product_id", "quantity", "unit_price"]
)
def test_missing_field_is_rejected(missing):
    data = {
        "customer_id": "C001",
        "product_id": "P001",
        "quantity": 2,
        "unit_price": 50.0,
    }
    del data[missing]
    with pytest.raises(ValidationError):
        Order(**data)


# --------------------------------------------------------------------------
# Identifiant de commande
# --------------------------------------------------------------------------
def test_order_id_format():
    event = build_order_event(make_order())
    assert re.fullmatch(r"ORD-[0-9A-F]{10}", event["order_id"])


def test_order_id_is_unique():
    order = make_order()
    ids = {build_order_event(order)["order_id"] for _ in range(200)}
    assert len(ids) == 200


# --------------------------------------------------------------------------
# Construction de l'événement
# --------------------------------------------------------------------------
def test_event_has_expected_fields():
    event = build_order_event(make_order())
    assert set(event) == {
        "order_id",
        "customer_id",
        "product_id",
        "quantity",
        "unit_price",
        "total_amount",
        "timestamp",
    }


def test_event_copies_order_values():
    order = make_order(customer_id="C100", product_id="P003", quantity=4, unit_price=49.9)
    event = build_order_event(order)
    assert event["customer_id"] == "C100"
    assert event["product_id"] == "P003"
    assert event["quantity"] == 4
    assert event["unit_price"] == 49.9


def test_event_timestamp_is_utc_iso8601():
    before = datetime.now(timezone.utc)
    event = build_order_event(make_order())
    after = datetime.now(timezone.utc)

    parsed = datetime.fromisoformat(event["timestamp"])
    assert parsed.tzinfo is not None
    assert parsed.utcoffset().total_seconds() == 0
    assert before <= parsed <= after


def test_event_is_valid_order_event_schema():
    """L'événement produit doit respecter le schéma de réponse de l'API."""
    event = build_order_event(make_order())
    assert OrderEvent(**event).total_amount == 100.0
