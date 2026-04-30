pipeline {
    agent any

    stages {
        stage('Clone Code') {
            steps {
                git branch: 'master', url: 'https://github.com/growwithnidhan/moneymap.git'
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '/opt/homebrew/bin/pip3 install -r requirements.txt'
            }
        }

        stage('Run Tests') {
            steps {
                sh 'python3 manage.py test'
            }
        }

        stage('Build Docker Image') {
            steps {
                sh 'docker build -t moneymap:latest .'
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                sh 'kubectl apply -f kubernetes/deployment.yml'
            }
        }
    }

    post {
        success {
            echo 'Pipeline succeeded!'
        }
        failure {
            echo 'Pipeline failed!'
        }
    }
}