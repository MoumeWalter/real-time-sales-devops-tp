import pytest
from app.main import Order, build_order_event


def test_order_total():
    order = Order(
        customer_id="C001",
        product_id="P001",
        quantity=2,
        unit_price=50.0,
    )
    event = build_order_event(order)
    assert event["total_amount"] == 100.0


def test_order_contains_order_id():
    order = Order(
        customer_id="C001",
        product_id="P001",
        quantity=1,
        unit_price=10.0,
    )
    event = build_order_event(order)
    assert event["order_id"].startswith("ORD-")


def test_quantity_must_be_positive():
    with pytest.raises(Exception):
        Order(
            customer_id="C001",
            product_id="P001",
            quantity=0,
            unit_price=10.0,
        )


# TODO étudiants :
# Ajouter des tests pour les autres règles métier.
