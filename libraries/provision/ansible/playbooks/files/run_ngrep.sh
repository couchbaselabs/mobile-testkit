#!/usr/bin/env bash

ngrep -d $1 -W byline port 4984 or port 4985 > /tmp/ngrep_$1.txt