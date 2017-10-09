#!/bin/bash

ABSOLUTE_ENV_SCRIPT=`readlink -f $0`

export SCRIPTS_DIR=`dirname ${ABSOLUTE_ENV_SCRIPT}`

export RENDER_CLIENT_JAR=`readlink -f render-ws-java-client-*-standalone.jar`

export BASE_JAVA_COMMAND="${JAVA_HOME}/bin/java -cp ${RENDER_CLIENT_JAR}"

# request memory up-front and use serial garbage collector to keep GC threads from taking over cluster node
export JAVA_MEMORY="${1:-1G}"
export JAVA_OPTS="-Xms${JAVA_MEMORY} -Xmx${JAVA_MEMORY} -Djava.awt.headless=true -XX:+UseSerialGC"

function runJavaCommandAndExit {
  COMMAND="${BASE_JAVA_COMMAND} ${JAVA_OPTS} $*"
  echo """
  Running: ${COMMAND}

"""
  ${COMMAND}
  exit $?
}
