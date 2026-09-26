# Architecture

## Composants

### Sales API

Responsable de :

- validation des commandes ;
- génération d'un identifiant ;
- calcul du montant ;
- publication Kafka.

### Kafka

Topic :

```text
sales.orders
```

### Spark

Consomme les événements Kafka, applique des validations simples et écrit les commandes traitées dans PostgreSQL.

### PostgreSQL

Table :

```text
processed_orders
```

### Jenkins

Orchestre la chaîne CI/CD.

### SonarQube

Analyse le code et applique un Quality Gate.

## Flux

```text
Client
  |
  | HTTP POST
  v
FastAPI
  |
  | Kafka event
  v
Kafka
  |
  | Structured Streaming
  v
PySpark
  |
  | JDBC
  v
PostgreSQL
```
