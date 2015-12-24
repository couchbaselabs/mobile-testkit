mkdir -p logs
gateload -workload=gateload_config.json > logs/gateload.log 2>&1

# Collect machine resource stats while gateload is running
python log_cpu.py
