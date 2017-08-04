### Building the image

```
docker build . -t liteserv-net
```

### Running the image

```
docker run --network cbl --name liteserv-net -it liteserv-net
```

### Talking to LiteServ
From a container on the 'cbl' network

```
curl http://liteserv-net:59840
```
