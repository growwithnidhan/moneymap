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
        sh '''
            export PATH="/opt/homebrew/bin:$PATH"
            export MYSQLCLIENT_CFLAGS=$(pkg-config --cflags mysqlclient 2>/dev/null || echo "-I/opt/homebrew/opt/mysql-client/include/mysql")
            export MYSQLCLIENT_LDFLAGS=$(pkg-config --libs mysqlclient 2>/dev/null || echo "-L/opt/homebrew/opt/mysql-client/lib -lmysqlclient")
            /opt/homebrew/bin/pip3 install -r requirements.txt --break-system-packages
        '''
    }
}

       stage('Run Tests') {
    steps {
        sh '''
            export PATH="/opt/homebrew/bin:$PATH"
            export MYSQLCLIENT_CFLAGS="-I/opt/homebrew/opt/mysql-client/include/mysql"
            export MYSQLCLIENT_LDFLAGS="-L/opt/homebrew/opt/mysql-client/lib -lmysqlclient"
            /opt/homebrew/bin/python3 manage.py test
        '''
    }
}

       stage('Build Docker Image') {
    steps {
        sh '/usr/local/bin/docker build -t moneymap:latest .'
    }
}

        stage('Deploy to Kubernetes') {
    steps {
        sh '/usr/local/bin/kubectl apply -f kubernetes/deployment.yml'
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