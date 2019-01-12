pipeline {
    agent none
    stages {
        stage('Build') {
            agent {
                docker {
                    image 'dsanderscan/jenkins-py3-0.1' 
                }
            }
            steps {
                checkout scm
                withEnv(["HOME=${env.WORKSPACE}"]) {
                    sh """
                      pwd
                      ls -als
                      python3 -m venv env
                      source ./env/bin/activate 
                      export PYTHONPATH="\$(pwd)/:\$(pwd)/tests"
                      export PERSISTER='{"engine_name": "secureredis", "parameters": {"host": "redis-12380.c83.us-east-1-2.ec2.cloud.redislabs.com", "port": 12380, "db": 0, "password": "${rediskey}"}}'
                      echo "*** PYTHONPATH=\${PYTHONPATH}"
                      python3 -m pip install -r requirements.txt
                      python3 -m unittest tests
                    """
                }
            }
        }
    }
}