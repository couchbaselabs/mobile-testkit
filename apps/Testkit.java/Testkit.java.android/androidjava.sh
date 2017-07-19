#!/bin/sh

function usage()
{
    echo "./androidjava.sh"
    echo "\t-h --help"
    echo "\t-t | --runtime-min=20"
    echo "\t-m | --max-docs=3"
    echo "\t-r | --replication-endpoint=blip://192.168.33.11:4984/db/"
    echo ""
}

while [ "$1" != "" ]; do
    case $1 in
        -h | --help)
            usage
            exit
            ;;
        -t | --runtime-min)
            RUNTIME=$2
            ;;
        -m | --max-docs)
            MAXDOCS=$2
            ;;
        -r | --replication-endpoint)
            REPLICATION_ENDPOINT=$2
            ;;
        *)
            echo "ERROR: unknown parameter $1"
            usage
            exit 1
            ;;
    esac
    shift
    shift
done

if [ ! "$RUNTIME" ] || [ ! "$MAXDOCS" ] || [ ! "$REPLICATION_ENDPOINT" ]
then
    usage
    exit 1
fi

echo "RUN TIME is $RUNTIME";
echo "MAX DOCS is $MAXDOCS";
echo "REPLICATION END POINT IS $REPLICATION_ENDPOINT";

#adb shell am start -n com.couchbase.androidclient/com.couchbase.androidclient.MainActivity -a android.intent.action.VIEW --es syncGatewayURL $REPLICATION_ENDPOINT --ei numOfDocs $MAXDOCS --ei scenarioRunTimeMinutes $RUNTIME

