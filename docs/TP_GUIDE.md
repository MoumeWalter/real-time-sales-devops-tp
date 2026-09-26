# Guide formateur — déroulé conseillé

## Phase 0 — Mise en route

Les étudiants doivent uniquement :

```bash
git clone <repo>
cd real-time-sales-devops-tp
docker compose up -d --build
docker compose ps
```

Puis vérifier :

- API : http://localhost:8000/docs
- Spark : http://localhost:8080
- Jenkins : http://localhost:8082
- SonarQube : http://localhost:9000

## Phase 1 — Comprendre le projet

Livrable : schéma d'architecture et description des flux.

## Phase 2 — Unit testing

Les étudiants complètent `tests/unit`.

Attendus :

- cas nominal ;
- valeurs limites ;
- données invalides ;
- règles métier ;
- couverture.

## Phase 3 — Integration testing

Activer progressivement les tests Kafka/API.

Attendu :

```text
API -> Kafka
```

Puis :

```text
Spark -> PostgreSQL
```

## Phase 4 — E2E

Scénario attendu :

```text
POST /api/orders
      |
      v
    Kafka
      |
      v
    Spark
      |
      v
 PostgreSQL
```

Le test doit attendre que le traitement soit terminé sans utiliser de `sleep` fixe excessif. Préférer une stratégie de polling avec timeout.

## Phase 5 — Jenkins

Les étudiants doivent transformer le Jenkinsfile fourni en vraie CI.

Pipeline cible :

1. Checkout
2. Install
3. Unit Tests
4. Integration Tests
5. Build
6. E2E
7. SonarQube
8. Quality Gate

## Phase 6 — SonarQube

Objectifs :

- connecter Jenkins à SonarQube ;
- publier l'analyse ;
- récupérer le Quality Gate ;
- bloquer la pipeline en cas d'échec.

## Phase 7 — Défense

Chaque groupe présente :

- architecture ;
- stratégie de tests ;
- pipeline Jenkins ;
- Quality Gate ;
- choix techniques ;
- difficultés rencontrées.
