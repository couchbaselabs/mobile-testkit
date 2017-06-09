# Pull the image
```
docker pull sethrosetter/testkit-net
```

# Run the App

--replication-endpoint is the endpoint <SyncGatewayUrl>:<DatabaseName> to run bidirectional replication against

```
dotnet run --replication-endpoint "blip://localhost:4984/db" --runtime-min 380
```