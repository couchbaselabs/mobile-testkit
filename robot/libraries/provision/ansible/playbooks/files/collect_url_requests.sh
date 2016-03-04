#!/bin/bash

usage () { echo "./collect_url_requests.sh -u URL -f output_file -t time"; }

# read the options
TEMP=`getopt -o r:f:t: -- "$@"`
eval set -- "$TEMP"


# extract options and their arguments into variables.
while true ; do
    case "$1" in
        -r|--request)
            case "$1" in
                "") shift 2 ;;
                *) REQUEST=$2 ; shift 2 ;;
            esac ;;
        -f|--file)
            case "$2" in
                "") shift 2 ;;
                *) LOG_FILE=$2 ; shift 2 ;;
            esac ;;
        -t|--time)
            case "$2" in
                "") shift 2 ;;
                *)  TIME=$2 ; shift 2 ;;
            esac ;;
        -h|--help) usage; exit;;
        --) shift ; break ;;
        *  ) echo "Unimplemented option: $1" >&2; exit 1;;
        #*  ) echo "Missing option arguments. Usage:" ; usage; exit 1;;
    esac
done

if [ -z REQUEST ]
then
   echo "No requested URL was passed"
   usage
   exit
fi

if [ -z "$LOG_FILE" ]
then
   echo "No output file was passed"
   usage
   exit
fi

if [ -z "$TIME" ]
then
   echo "No time was passed"
   usage
   exit
fi

rm -rf $LOG_FILE

while true; do
    curl --silent $REQUEST >> $LOG_FILE
	sleep $TIME
done