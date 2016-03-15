while [ 1 ]
do
    outfile=expvar_$(date +%s)
    curl localhost:9876/debug/vars -o ${outfile}.json
    echo "Saved output to $outfile"
    sleep 60
done
