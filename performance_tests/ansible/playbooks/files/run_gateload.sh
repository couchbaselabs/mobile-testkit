mkdir -p logs
gateload -workload=gateload_config.json > logs/gateload.log 2>&1
