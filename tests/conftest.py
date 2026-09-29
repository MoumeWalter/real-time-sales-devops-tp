import pytest

from tests.helpers import delete_orders


@pytest.fixture
def order_cleanup():
    """Liste d'order_id à supprimer de PostgreSQL à la fin du test."""
    order_ids = []
    yield order_ids
    try:
        delete_orders(order_ids)
    except Exception as exc:  # le nettoyage ne doit jamais casser un test
        print(f"Nettoyage impossible : {exc!r}")
