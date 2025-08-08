# betriebskostenabrechnung

If you read this, you know what this is.

```bash
docker build -t betriebskostenabrechnung .
docker run -v $(pwd)/db/:/code/db/ \
	--name betriebskostenabrechnung \
	--restart always \
	-d \
	-p 127.0.0.1:8000:8000 \
	betriebskostenabrechnung
```
