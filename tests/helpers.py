"""Utilitaires communs aux tests d'intégration et E2E.

Les adresses des services sont lues dans des variables d'environnement :
- depuis votre machine : les valeurs par défaut (localhost) suffisent ;
- depuis Jenkins (réseau Docker) : on les surcharge dans le Jenkinsfile
  (API_URL=http://sales-api:8000, KAFKA_TEST_BOOTSTRAP=kafka:29092,
  POSTGRES_HOST=postgres).
"""
import json
import os
import time
import uuid
from contextlib import closing
from datetime import datetime, timezone

API_URL = os.getenv("API_URL", "http://localhost:8000")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_TEST_BOOTSTRAP", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "sales.orders")

PG_PARAMS = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB", "sales"),
    "user": os.getenv("POSTGRES_USER", "sales"),
    "password": os.getenv("POSTGRES_PASSWORD", "sales"),
}

# Délai maximal d'attente du traitement Spark (démarrage à froid inclus).
PIPELINE_TIMEOUT = float(os.getenv("PIPELINE_TIMEOUT", "90"))

ORDER_COLUMNS = (
    "order_id, customer_id, product_id, quantity, unit_price, "
    "total_amount, event_timestamp, processed_at"
)


# --------------------------------------------------------------------------
# Polling avec timeout (remplace time.sleep)
# --------------------------------------------------------------------------
def wait_until(predicate, timeout=30.0, interval=1.0, description="condition"):
    """Appelle `predicate` jusqu'à obtenir une valeur "truthy".

    Renvoie cette valeur. Si le délai est dépassé, lève une AssertionError
    explicite : le test échoue proprement au lieu de bloquer.
    """
    deadline = time.monotonic() + timeout
    last_error = None
    while True:
        try:
            result = predicate()
            if result:
                return result
        except Exception as exc:  # service pas encore prêt : on réessaie
            last_error = exc
        if time.monotonic() >= deadline:
            detail = f" Dernière erreur : {last_error!r}." if last_error else ""
            raise AssertionError(
                f"Timeout après {timeout:.0f}s en attendant : {description}.{detail}"
            )
        time.sleep(interval)


# --------------------------------------------------------------------------
# PostgreSQL
# --------------------------------------------------------------------------
def pg_connect():
    import psycopg2

    return psycopg2.connect(**PG_PARAMS)


def fetch_order(order_id):
    """Renvoie la ligne de processed_orders sous forme de dict, ou None."""
    with closing(pg_connect()) as conn, conn.cursor() as cur:
        cur.execute(
            f"SELECT {ORDER_COLUMNS} FROM processed_orders WHERE order_id = %s",
            (order_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return dict(zip([col[0] for col in cur.description], row))


def delete_orders(order_ids):
    if not order_ids:
        return
    with closing(pg_connect()) as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM processed_orders WHERE order_id = ANY(%s)",
            (list(order_ids),),
        )
        conn.commit()


# --------------------------------------------------------------------------
# Kafka
# --------------------------------------------------------------------------
def _safe_json(raw):
    try:
        return json.loads(raw.decode("utf-8"))
    except (ValueError, AttributeError):
        return None


def make_consumer():
    """Consumer positionné au début du topic (sans groupe, sans commit)."""
    from kafka import KafkaConsumer, TopicPartition

    consumer = KafkaConsumer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id=None,
        enable_auto_commit=False,
        value_deserializer=_safe_json,
    )
    partitions = wait_until(
        lambda: consumer.partitions_for_topic(KAFKA_TOPIC),
        timeout=30,
        description=f"l'existence du topic {KAFKA_TOPIC}",
    )
    topic_partitions = [TopicPartition(KAFKA_TOPIC, p) for p in partitions]
    consumer.assign(topic_partitions)
    consumer.seek_to_beginning(*topic_partitions)
    return consumer


def kafka_total_offset(consumer):
    """Nombre total de messages écrits dans le topic (somme des end offsets)."""
    return sum(consumer.end_offsets(list(consumer.assignment())).values())


def find_kafka_message(consumer, order_id, timeout=30.0):
    """Attend qu'un message contenant cet order_id apparaisse dans le topic."""
    found = []

    def _poll():
        for records in consumer.poll(timeout_ms=1000).values():
            for record in records:
                value = record.value
                if isinstance(value, dict) and value.get("order_id") == order_id:
                    found.append(value)
        return found[0] if found else None

    return wait_until(
        _poll,
        timeout=timeout,
        interval=0.1,
        description=f"le message {order_id} dans le topic {KAFKA_TOPIC}",
    )


def publish_event(event):
    """Publie directement un événement dans Kafka (sans passer par l'API)."""
    from kafka import KafkaProducer

    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    try:
        producer.send(KAFKA_TOPIC, value=event).get(timeout=10)
        producer.flush()
    finally:
        producer.close()


# --------------------------------------------------------------------------
# Données de test
# --------------------------------------------------------------------------
def new_order_id(prefix="ORD-IT"):
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def make_event(order_id, customer_id="C-SPARK", product_id="P001",
               quantity=3, unit_price=100.0):
    return {
        "order_id": order_id,
        "customer_id": customer_id,
        "product_id": product_id,
        "quantity": quantity,
        "unit_price": unit_price,
        "total_amount": round(quantity * unit_price, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
