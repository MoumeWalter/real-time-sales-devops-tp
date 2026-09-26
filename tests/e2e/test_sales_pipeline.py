import os
import pytest

RUN_E2E = os.getenv("RUN_E2E_TESTS", "false").lower() == "true"

pytestmark = pytest.mark.skipif(
    not RUN_E2E,
    reason="E2E tests disabled. Set RUN_E2E_TESTS=true."
)

# TODO étudiants :
# Implémenter le scénario :
# API -> Kafka -> Spark -> PostgreSQL
#
# Le test doit :
# 1. envoyer une commande ;
# 2. attendre le traitement Spark ;
# 3. vérifier que la commande existe dans PostgreSQL ;
# 4. vérifier les valeurs calculées.
