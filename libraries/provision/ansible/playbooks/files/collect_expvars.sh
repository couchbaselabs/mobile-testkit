SLEEP_TIME=${1:-60}

while [ 1 ]
do
    outfile=expvar_$(date +%s)
    curl localhost:9876/debug/vars -o ${outfile}.json
    echo "Saved output to $outfile"
    sleep $SLEEP_TIME
done
