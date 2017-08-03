### Building the image

```
docker build . -t liteserv-net
```

### Running the image

```
docker run --network test-network -it liteserv-net
```
