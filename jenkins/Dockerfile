# Servidor Jenkins del proyecto To-Do
# Imagenes oficiales con version fija (no "latest")

# Etapa 1: de aqui solo tomamos el cliente de Docker y sus plugins (compose, buildx)
FROM docker:29.10.0-cli AS dockercli

# Etapa 2: Jenkins LTS con Java 21
FROM jenkins/jenkins:2.580.2-lts-jdk21

USER root
# Cliente de Docker para que los pipelines construyan imagenes y usen docker compose.
# El motor (daemon) es el del equipo anfitrion, al que se llega por /var/run/docker.sock
COPY --from=dockercli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=dockercli /usr/local/libexec/docker/cli-plugins/ /usr/local/libexec/docker/cli-plugins/

USER jenkins

# Sin asistente de instalacion: toda la configuracion llega por Configuration as Code (JCasC)
ENV JAVA_OPTS="-Djenkins.install.runSetupWizard=false" \
    CASC_JENKINS_CONFIG=/usr/share/jenkins/casc/jenkins.yaml

# Plugins: Git/GitHub, Pipeline, Docker Pipeline, JCasC, Job DSL, JUnit, vistas de etapas
COPY --chown=jenkins:jenkins plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

# Configuracion de Jenkins como codigo (usuario, credenciales y job)
COPY --chown=jenkins:jenkins jenkins.yaml /usr/share/jenkins/casc/jenkins.yaml

EXPOSE 8080
