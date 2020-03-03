#!/bin/sh

SERVICE_STATUS=$1
BINARY_LOCATION=$2
OUTPUT_LOCATION=$3
JAVA_HOME_LOCATION=$4
JSVC_LOCATION=$5


# Setup variables
EXEC=${JSVC_LOCATION}
JAVA_HOME=${JAVA_HOME_LOCATION}
CLASS_PATH=${BINARY_LOCATION}
CLASS=com.couchbase.mobiletestkit.javatestserver.TestServerMain
USER=root
PID=${OUTPUT_LOCATION}/testserver-java.pid
LOG_OUT=${OUTPUT_LOCATION}/testserver-java.out
LOG_ERR=${OUTPUT_LOCATION}/testserver-java.err

do_exec()
{
    $EXEC -home "$JAVA_HOME" -cp $CLASS_PATH -user $USER -outfile $LOG_OUT -errfile $LOG_ERR -pidfile $PID $1 $CLASS
}

case "${SERVICE_STATUS}" in
    start)
        do_exec
            ;;
    stop)
        do_exec "-stop"
            ;;
    restart)
        if [ -f "$PID" ]; then
            do_exec "-stop"
            do_exec
        else
            echo "service not running, will do nothing"
            exit 1
        fi
            ;;
    *)
            echo "usage: daemon {start|stop|restart}" >&2
            exit 3
            ;;
esac
