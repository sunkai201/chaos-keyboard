#!/bin/sh
# Gradle startup script for Unix

APP_HOME=$(cd "${0%/*}" && pwd)

if [ -n "$JAVA_HOME" ]; then
  JAVA_EXE="$JAVA_HOME/bin/java"
else
  JAVA_EXE=java
fi

CLASSPATH="$APP_HOME/gradle/wrapper/gradle-wrapper.jar"

exec "$JAVA_EXE" "-Xmx64m" "-Xms64m" -classpath "$CLASSPATH" \
  org.gradle.wrapper.GradleWrapperMain "$@"
