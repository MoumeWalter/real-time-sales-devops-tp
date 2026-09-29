FROM jenkins/jenkins:lts-jdk17

USER root

# Outils nécessaires au pipeline : Docker CLI, Python (+ venv), Git, curl
RUN apt-get update \
    && apt-get install -y docker.io python3 python3-pip python3-venv git curl \
    && rm -rf /var/lib/apt/lists/*

# Plugin "docker compose" (v2) : absent du paquet docker.io
RUN mkdir -p /usr/local/lib/docker/cli-plugins \
    && curl -fsSL "https://github.com/docker/compose/releases/download/v2.29.7/docker-compose-linux-$(uname -m)" \
       -o /usr/local/lib/docker/cli-plugins/docker-compose \
    && chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

RUN python3 --version && docker --version && docker compose version

USER jenkins

# Le setup wizard est désactivé : on installe explicitement les plugins requis
RUN jenkins-plugin-cli --plugins \
    workflow-aggregator \
    git \
    junit \
    sonar \
    credentials-binding \
    timestamper
