#!/usr/bin/env bash

# Requires that Nexus_5_API_23_x86 and 4_7_WXGA_API_15 avds have been set up.

apiversion=$1

if [ "$apiversion" == "23" ]; then
    emulator -scale 0.25 @Nexus_5_API_23 &
elif [ "$apiversion" == "21" ]; then
    emulator -scale 0.5 @Nexus_5_API_21 &
elif [ "$apiversion" == "15" ]; then
    emulator -scale 0.5 @Nexus_5_API_15 &
else
    echo "Unsupported API version. Did not launch emulator"
    echo "Usage: './start_emulator.sh 15'"
    exit 1
fi
