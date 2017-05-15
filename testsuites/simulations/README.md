### Running the simulation (End to end, XATTRs and the travel sample)

1. Download Couchbase Server (5.0+) / Sync Gateway (1.5+)
2. Create travel sample bucket / bucket user on Couchbase Server
3. Start Sync Gateway targeting Couchbase Server
```
./sync_gateway testsuites/simulations/sync.json 2>&1 | tee sgoutput.log
```
4. Open Travel.NET/Travel.NET.sln
5. Run the app
    - This will pull all of the travel docs down to Lite
    - Each doc will be updated via Lite
6. Wait until output stops and you see `Waiting for SDK to perform updates ...`
7. Open a new terminal and run `python Travel.NET/validate_and_updater.py`
    - This validates all changes on Lite on are pushed and visible via SDK
    - This will update all of the docs via the Couchbase Server Python SDK
8. Once, the python script exits, return to the app output and press enter
    - The app will now poll until it sees all of the SDK revsions. 