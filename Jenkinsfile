pipeline {
    agent any

    environment {
        PYTHON = 'python3'
        RUN_INTEGRATION_TESTS = 'false'
        RUN_E2E_TESTS = 'false'
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
            }
        }

        stage('Install') {
            steps {
                sh 'python3 -m pip install --user -r requirements.txt'
            }
        }

        stage('Unit Tests') {
            steps {
                sh '''
                    python3 -m pytest tests/unit \
                      --cov=app \
                      --cov-report=xml:coverage.xml \
                      --cov-report=term-missing
                '''
            }
        }

        stage('Integration Tests') {
            steps {
                sh '''
                    echo "TODO: enable integration tests after configuring Kafka."
                    python3 -m pytest tests/integration
                '''
            }
        }

        stage('Build') {
            steps {
                sh 'docker compose build sales-api spark-streaming'
            }
        }

        stage('E2E Tests') {
            steps {
                sh '''
                    echo "TODO: students must activate the complete E2E scenario."
                    python3 -m pytest tests/e2e
                '''
            }
        }

        stage('SonarQube') {
            steps {
                echo 'TODO: configure SonarQube Scanner / server credentials.'
            }
        }

        stage('Quality Gate') {
            steps {
                echo 'TODO: waitForQualityGate() after SonarQube integration.'
            }
        }
    }

    post {
        always {
            junit allowEmptyResults: true, testResults: '**/test-results.xml'
            archiveArtifacts allowEmptyArchive: true, artifacts: 'coverage.xml'
        }
    }
}
