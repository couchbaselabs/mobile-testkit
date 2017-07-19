#!/bin/sh


#ENVIRONMENT="dev"
#DB_PATH="/data/db"
function usage()
{
    echo "./simple_args_parsing.sh"
    echo "\t-h --help"
    echo "\t-t | --runtime-min=20"
    echo "\t-m | --max-docs=3"
    echo "\t-r | --replication-endpoint=blip://192.168.33.11:4984/db/"
    echo ""
}

while [ "$1" != "" ]; do
    #PARAM=`echo $1 | awk -F= '{print $1}'`
    #VALUE=`echo $1 | awk -F= '{print $2}'`
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
            echo "ERROR: unknown parameter \"$PARAM\""
            usage
            exit 1
            ;;
    esac
    shift
    shift
done

adb shell am start -n com.couchbase.androidclient/com.couchbase.androidclient.MainActivity -a android.intent.action.VIEW --es syncGatewayURL $REPLICATION_ENDPOINT --ei numOfDocs $MAXDOCS --ei scenarioRunTimeMinutes $RUNTIME

echo "RUN TIME is $RUNTIME";
echo "MAX DOCS is $MAXDOCS";
echo "REPLICATION END POINT IS $REPLICATION_ENDPOINT";
