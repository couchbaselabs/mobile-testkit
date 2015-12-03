#!/bin/bash

x=1
exit_status=1

while [ $exit_status != 0 ]
do
  lsof -i :4985
  exit_status=$?
  echo $exit_status

  x=$(( $x + 1 ))
  # 2 min and no launch, fail
  if [ $x -gt 120 ]
  then
    echo "sync_gateway did not launch in 2 min"
    exit 1
  fi

  sleep 1
done