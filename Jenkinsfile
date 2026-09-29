pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
    }

    environment {
        // Adresses des services vus depuis le conteneur Jenkins (réseau data-platform)
        API_URL              = 'http://sales-api:8000'
        KAFKA_TEST_BOOTSTRAP = 'kafka:29092'
        KAFKA_TOPIC          = 'sales.orders'
        POSTGRES_HOST        = 'postgres'
        PIPELINE_TIMEOUT     = '120'
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Environment') {
            steps {
                sh 'python3 --version'
                sh 'docker --version'
                sh 'docker compose version'
            }
        }

        stage('Install') {
            steps {
                sh '''
                    python3 -m venv .venv
                    .venv/bin/python -m pip install --upgrade pip
                    .venv/bin/python -m pip install -r requirements-dev.txt
                '''
            }
        }

        stage('Unit Tests') {
            steps {
                sh '''
                    .venv/bin/python -m pytest tests/unit -v \
                      --cov=app \
                      --cov-report=xml:coverage.xml \
                      --cov-report=term-missing \
                      --junitxml=test-results/unit.xml
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'test-results/unit.xml'
                }
            }
        }

        stage('Verify Infrastructure') {
            steps {
                sh '''
                    curl -fsS "$API_URL/api/health"
                    echo
                    RUNNING=$(docker inspect -f '{{.State.Running}}' sales-spark-streaming)
                    if [ "$RUNNING" != "true" ]; then
                        echo "sales-spark-streaming is not running: docker compose up -d spark-streaming"
                        exit 1
                    fi
                '''
            }
        }

        stage('Integration Tests') {
            environment {
                RUN_INTEGRATION_TESTS = 'true'
            }
            steps {
                sh '''
                    .venv/bin/python -m pytest tests/integration -v \
                      --junitxml=test-results/integration.xml
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'test-results/integration.xml'
                }
            }
        }

        stage('Build') {
            steps {
                sh 'docker compose build sales-api spark-streaming'
            }
        }

        stage('E2E Tests') {
            environment {
                RUN_E2E_TESTS = 'true'
            }
            steps {
                sh '''
                    .venv/bin/python -m pytest tests/e2e -v \
                      --junitxml=test-results/e2e.xml
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'test-results/e2e.xml'
                }
            }
        }

        stage('SonarQube') {
            steps {
                echo 'TODO: analyse SonarQube (étape suivante du TP).'
            }
        }

        stage('Quality Gate') {
            steps {
                echo 'TODO: waitForQualityGate() (étape suivante du TP).'
            }
        }
    }

    post {
        always {
            archiveArtifacts allowEmptyArchive: true, artifacts: 'coverage.xml, test-results/*.xml'
        }
        success {
            echo 'Pipeline OK'
        }
        failure {
            echo 'Pipeline FAILED : consulter les logs de l\'étape en échec.'
        }
    }
}
