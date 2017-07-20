#!/bin/bash

SG_LOG_FILE="/home/sync_gateway/logs/sync_gateway_error.log"
SGA_LOG_FILE="/home/sg_accel/logs/sg_accel_error.log"
SYS_LOG="/var/log/messages"

# Check OOM logs in sys log
if [ -f $SYS_LOG ]; then
	OUT=$(grep -i "Out of memory: Kill process" $SYS_LOG | grep -i sync_gateway)
	if [ ! -z "$OUT" ]; then
		echo "Found Out of memory errors for sync_gateway in $SYS_LOG"
		exit 1
	fi

	OUT=$(grep -i "Out of memory: Kill process" $SYS_LOG | grep -i sg_accel)
	if [ ! -z "$OUT" ]; then
		echo "Found Out of memory errors for sg_accel in $SYS_LOG"
		exit 1
	fi
fi

# Array of error keys we look for in SG/SGAccel logs
SG_ERRORS=('panic' 'data race' 'SIGSEGV' 'nil pointer dereference')
if [ -f $SG_LOG_FILE ]; then
	for ((i = 0; i < ${#SG_ERRORS[@]}; i++));do
		OUT=$(grep -i "${SG_ERRORS[$i]}" $SG_LOG_FILE)
		if [ ! -z "$OUT" ]; then
			echo "Found ${SG_ERRORS[$i]} in $SG_LOG_FILE"
			exit 1
		fi
	done
fi

if [ -f $SGA_LOG_FILE ]; then
	for ((i = 0; i < ${#SG_ERRORS[@]}; i++));do
		OUT=$(grep -i "${SG_ERRORS[$i]}" $SGA_LOG_FILE)
		if [ ! -z "$OUT" ]; then
			echo "Found ${SG_ERRORS[$i]} in $SGA_LOG_FILE"
			exit 1
		fi
	done
fi
