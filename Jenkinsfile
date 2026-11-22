// Pipeline de integracion continua del proyecto To-Do (Flask + PostgreSQL)
// Etapas: Checkout -> Pruebas unitarias -> Build -> Test de integracion, y bloque post.

pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '30'))
        timeout(time: 20, unit: 'MINUTES')
    }

    // Jenkins revisa GitHub cada ~2 minutos y lanza el pipeline si hay commits nuevos
    triggers {
        pollSCM('H/2 * * * *')
    }

    environment {
        // Datos NO secretos; la contrasena llega desde las credenciales de Jenkins
        POSTGRES_DB          = 'tareas_db'
        POSTGRES_USER        = 'tareas_user'
        IMAGE_TAG            = "ci-${env.BUILD_NUMBER}"
        COMPOSE_PROJECT_NAME = 'todo-ci'
        COMPOSE_FILES        = '-f docker-compose.yml -f ci/docker-compose.ci.yml'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git log -1 --pretty="Commit: %h - %s (%an)"'
            }
        }

        stage('Pruebas unitarias') {
            // Contenedor efimero de Python solo para las pruebas; se elimina al terminar
            agent {
                docker {
                    image 'python:3.12.7-slim'
                    reuseNode true
                }
            }
            steps {
                dir('app') {
                    sh '''
                        python -m venv .venv
                        .venv/bin/pip install --quiet --no-cache-dir -r requirements-dev.txt
                        .venv/bin/python -m pytest -v --junitxml=reports/junit.xml
                    '''
                }
            }
            post {
                always {
                    junit 'app/reports/junit.xml'
                }
            }
        }

        stage('Build') {
            steps {
                sh 'docker build -t todo-app:${IMAGE_TAG} ./app'
                sh 'docker build -t todo-db:${IMAGE_TAG} ./db'
                sh 'docker image ls --filter reference="todo-*:${IMAGE_TAG}"'
            }
        }

        stage('Test de integracion') {
            steps {
                withCredentials([string(credentialsId: 'postgres-password', variable: 'POSTGRES_PASSWORD')]) {
                    sh 'docker compose ${COMPOSE_FILES} up -d --wait --wait-timeout 120'
                    sh 'docker compose ${COMPOSE_FILES} ps'
                    // La prueba corre DENTRO del contenedor app y llega a la base de datos por el nombre "db"
                    sh 'docker compose ${COMPOSE_FILES} exec -T app python - < ci/prueba_comunicacion.py'
                }
            }
        }
    }

    post {
        always {
            withCredentials([string(credentialsId: 'postgres-password', variable: 'POSTGRES_PASSWORD')]) {
                sh 'docker compose ${COMPOSE_FILES} logs --no-color --tail=30 || true'
                sh 'docker compose ${COMPOSE_FILES} down -v --remove-orphans || true'
            }
            sh 'docker image rm todo-app:${IMAGE_TAG} todo-db:${IMAGE_TAG} || true'
        }
        success {
            echo 'BUILD EXITOSO: pruebas unitarias, imagenes y comunicacion app -> db verificadas.'
        }
        failure {
            echo 'BUILD FALLIDO: revisa la etapa en rojo. El codigo con errores no llega a convertirse en imagen.'
        }
    }
}
