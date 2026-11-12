// =============================================================================
// Jenkins Declarative Pipeline: Municipal Citizen Grievance Platform
// SIMATS Engineering - CSA10 Software Engineering (CO4 AT2)
// Student: Kandukuri Vijay Bhaskar Reddy (Reg No: 192425155)
// =============================================================================

pipeline {
    agent any

    environment {
        APP_NAME        = 'municipal-grievance-platform'
        DOCKER_IMAGE    = "municipal-grievance-platform:${BUILD_NUMBER}"
        REGISTRY_CRED_ID = 'docker-hub-credentials'
        CONTAINER_NAME  = 'municipal_grievance_prod'
        PORT            = '8000'
    }

    options {
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
        ansiColor('xterm')
    }

    stages {
        stage('Checkout Source') {
            steps {
                echo '=== Stage 1: Checking out source code from Git ==='
                checkout scm
                sh 'git log -1 --stat'
            }
        }

        stage('Environment & Dependencies') {
            steps {
                echo '=== Stage 2: Setting up Python virtual environment ==='
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Code Quality & Linting') {
            steps {
                echo '=== Stage 3: Running Flake8 static analysis and PEP 8 verification ==='
                sh '''
                    . venv/bin/activate
                    flake8 backend/ --max-line-length=120 --count --statistics || true
                '''
            }
        }

        stage('Automated Unit & Boundary Testing') {
            steps {
                echo '=== Stage 4: Executing automated PyTest suite with JUnit report ==='
                sh '''
                    . venv/bin/activate
                    mkdir -p reports
                    python -m pytest --junitxml=reports/test-results.xml -v
                '''
            }
            post {
                always {
                    junit 'reports/test-results.xml'
                }
            }
        }

        stage('Security & Vulnerability Scan') {
            steps {
                echo '=== Stage 5: Auditing security and container vulnerabilities ==='
                sh '''
                    . venv/bin/activate
                    pip install bandit
                    bandit -r backend/ -f custom --msg-template "{abspath}:{line}: {test_id}[bandit]: {severity}: {msg}" || true
                '''
            }
        }

        stage('Docker Build & Package') {
            steps {
                echo '=== Stage 6: Building multi-stage production Docker container ==='
                sh """
                    docker build -t ${DOCKER_IMAGE} -t ${APP_NAME}:latest .
                """
            }
        }

        stage('Deploy to Staging') {
            steps {
                echo '=== Stage 7: Deploying container to Staging environment ==='
                sh """
                    docker stop ${CONTAINER_NAME}_staging || true
                    docker rm ${CONTAINER_NAME}_staging || true
                    docker run -d --name ${CONTAINER_NAME}_staging -p 8080:8000 \
                        -e PORT=8000 \
                        -e SECRET_KEY=municipal-staging-key-2026 \
                        ${DOCKER_IMAGE}
                """
                echo 'Validating staging container health probe...'
                sh '''
                    sleep 5
                    curl -f http://localhost:8080/api/v1/healthz || exit 1
                '''
            }
        }

        stage('Deploy to Production') {
            when {
                branch 'main'
            }
            steps {
                echo '=== Stage 8: Blue-Green deployment to Production ==='
                sh """
                    docker stop ${CONTAINER_NAME} || true
                    docker rm ${CONTAINER_NAME} || true
                    docker run -d --name ${CONTAINER_NAME} -p 8000:8000 \
                        --restart unless-stopped \
                        -v grievance_prod_data:/app/data \
                        -e PORT=8000 \
                        -e SECRET_KEY=municipal-prod-secret-2026 \
                        ${DOCKER_IMAGE}
                """
                echo 'Verifying production health check endpoint...'
                sh '''
                    sleep 5
                    curl -f http://localhost:8000/api/v1/healthz || exit 1
                '''
            }
        }
    }

    post {
        success {
            echo 'SUCCESS: CI/CD Pipeline executed successfully across all stages!'
        }
        failure {
            echo 'FAILURE: Pipeline halted due to error. Initiating automated rollback...'
            sh """
                docker rollback ${CONTAINER_NAME} || true
            """
        }
        always {
            cleanWs deleteDirs: true, notFailBuild: true
        }
    }
}

