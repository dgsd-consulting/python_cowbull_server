// -------------------------------------------------------------------
//
// Module:         python_cowbull_server
// Submodule:      Jenkinsfile
// Environments:   all
// Purpose:        Jenkins scripted pipeline to perform the CI and CD
//                 build of the python cowbull server image.
//                 NOTE: Scripted pipeline
//
// Created on:     30 July 2019
// Created by:     David Sanders
// Creator email:  dsanderscanada@nospam-gmail.com
//
// -------------------------------------------------------------------
// Modifed On   | Modified By                 | Release Notes
// -------------------------------------------------------------------
// 30 Jul 2019  | David Sanders               | First release.
// -------------------------------------------------------------------
// 06 Aug 2019  | David Sanders               | Change python3 to use
//              |                             | default python rather
//              |                             | than specific version.
// -------------------------------------------------------------------
// 06 Aug 2019  | David Sanders               | Add multi-branch
//              |                             | support and push non-
//              |                             | master branches as dev
//              |                             | and promote major/minor
//              |                             | to year month format.
// -------------------------------------------------------------------
// 19 Aug 2019  | David Sanders               | Combine k8s plug-in
//              |                             | with Docker for simpler
//              |                             | builds.
// -------------------------------------------------------------------
// 20 Aug 2019  | David Sanders               | Move yaml manifest for
//              |                             | build containers to an
//              |                             | external file and read
//              |                             | on pipeline execution.
//              |                             | Add comments.
//              |                             | Update pip config.
// -------------------------------------------------------------------

// Define the variables used in the pipeline
def major = '19'    // The major version of the build - Major.Minor.Build
def minor = '08'    // The minor version of the build - Major.Minor.Build
def imageName = ''  // Variable to hold image name; depends on branch
def privateImage = '' // Variable for private hub image name
def yamlString = "" // Variable used to contain yaml manifests which are
                    // loaded from file.

// DNS name and protocol for connecting to the Docker service
// TODO: Make into a global variable
def dockerServer = "tcp://jenkins-service.jenkins.svc.cluster.local:2375"

// Preparation stage. Checks out the source and loads the yaml manifests
// used during the pipeline. see ./jenkins/build-containers.yaml
node {
    stage('Prepare environment') {
        checkout scm
        yamlString = readFile "jenkins/build-containers.yaml"
    }
}

// Define the pod templates to, run the containers and execute the
// pipeline.
podTemplate(yaml: "${yamlString}") {
  node(POD_LABEL) {

    // Setup environment stage. Set the image name depending on the
    // branch, use the python container and install the required pypi
    // packages from requirements.txt
    stage('Setup environment') {
        if ( (env.BRANCH_NAME).equals('master') ) {
            imageName = "dsanderscan/cowbull:${major}.${minor}.${env.BUILD_NUMBER}"
            privateImage = "cowbull:${major}.${minor}.${env.BUILD_NUMBER}"
        } else {
            imageName = "dsanderscan/cowbull:${env.BRANCH_NAME}.${env.BUILD_NUMBER}"
            privateImage = "cowbull:${env.BRANCH_NAME}.${env.BUILD_NUMBER}"
        }
        checkout scm
        container('python') {
            withCredentials([file(credentialsId: 'pip-conf-file', variable: 'pipconfig')]) {
                sh """
                    cp $pipconfig /etc/pip.conf
                    python --version
                    python -m pip install -r requirements.txt
                """
            }
        }
    }

    // Simple stage to ensure that redis is reachable; redis is required
    // for unit and system tests later in the pipeline.
    stage('Verify Redis is running') {
        container('redis') {
            sh 'redis-cli ping'
        }
    }

    // Execute the unit tests; while these should have already been
    // processed, they are re-run to ensure the source software is
    // good. During unit test, the application uses the file system
    // as the persister.
    stage('Execute Python unit tests') {
        container('python') {
            try {
                sh """
                    export PYTHONPATH="\$(pwd)"
                    coverage run unittests/main.py
                    coverage xml -i
                """
            } finally {
                junit 'unittest-reports/*.xml'
            }
        }
    }

    // Execute the system tests; verify that the system as a whole is
    // operating as expected. Redis is used as the persister.
    stage('Execute Python system tests') {
        container('python') {
            try {
                sh """
                    export PYTHONPATH="\$(pwd)"
                    export PERSISTER='{"engine_name": "redis", "parameters": {"host": "localhost", "port": 6379, "db": 0, "password": ""}}'
                    export LOGGING_LEVEL=30
                    python systests/main.py
                """
            } finally {
                junit 'systest-reports/*.xml'
            }
        }
    }

    // Collect the coverage reports and pass them to the sonarqube
    // scanner for analysis.
    stage('Sonarqube code coverage') {
        container('maven') {
            def scannerHome = tool 'SonarQube Scanner';
            withSonarQubeEnv('Sonarqube') {
                sh """
                    rm -rf *.pyc
                    rm -f /var/jenkins_home/workspace/cowbull-server/.scannerwork/report-task.txt
                    rm -f /var/jenkins_home/workspace/cowbull-server/.sonar/report-task.txt
                    echo "Run sonar scanner"
                    chmod +x ${scannerHome}/bin/sonar-scanner
                    ${scannerHome}/bin/sonar-scanner -X -Dproject.settings=./sonar-project.properties -Dsonar.python.coverage.reportPath=./coverage.xml -Dsonar.projectVersion="${major}"."${minor}"."${env.BUILD_NUMBER}"
                """
            }
        }
    }

    // Check the quality of the project. In this stage, the 
    // abortPipeline is set to true and ensures the pipeline aborts
    // if the code quality is low - it could be set to false to continue
    // the pipeline if required.
    stage('Quality Gate') {
        container('maven') {
            def scannerHome = tool 'SonarQube Scanner';
            timeout(time: 10, unit: 'MINUTES') {
                waitForQualityGate abortPipeline: true
            }
        }
    }

    // Build the application into a docker image and push it to the
    // Docker Hub and the private registry.
    // TODO: the registry URLs should be global variables.
    stage('Docker Build') {
        container('docker') {
            docker.withServer("$dockerServer") {
                docker.withRegistry('http://k8s-master:32081', 'nexus-oss') {
                    def customImage = docker.build("${privateImage}", "-f Dockerfile .")
                    customImage.push()
                }
                docker.withRegistry('https://registry-1.docker.io', 'dockerhub') {
                    def customImage = docker.build("${imageName}", "-f Dockerfile .")
                    customImage.push()
                }
            }
            sh 'echo "docker.io/${imageName}" > anchore_images'
        }
    }

    stage('Image Security scan') {
        anchore engineCredentialsId: 'azure-azadmin', name: 'anchore_images'
    }

    // Tidy up. Nothing happens here at present.
    stage('Tidy up') {
        container('docker') {
            sh """
                echo "Doing some tidying up :) "
            """
        }
    }
  }
}
