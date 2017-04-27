The key point is that the IP camera supports retrieving snapshots via HTTP. For example, my IP camera provides the interface to retrieve snapshot:

```
http://<ip-address>/cgi-bin/encoder?USER=<username>&PWD=<password>&Channel=1&SNAPSHOT
```

Another key point is that the snapshot resolution does not need to be large. If the detected object occupies 80% area in an image, resolution 640x480 is sufficient for inference.
