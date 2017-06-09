# Build the image
```
docker build -t testkit-net .
```

# Run the App

--replication-endpoint is the endpoint <SyncGatewayUrl>:<DatabaseName> to run bidirectional replication against
--runtime-min is the number of minutes to run the scenarios for

```
docker run testkit-net dotnet run --replication-endpoint "blip://localhost:4984/db" --runtime-min 380
```