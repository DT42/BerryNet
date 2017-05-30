# Setup General Purpose IP Camera

Steps to connect your IP camera to BerryNet:

1. Get snapshot URL of the IP camera.

    The [camera connection database](https://www.ispyconnect.com/sources.aspx) can generate snapshot URL if your IP camera is supported.

    The key is that the IP camera supports retrieving snapshots via HTTP. For example, my IP camera provides the interface to retrieve snapshot:

    ```
    http://<ip-address>/cgi-bin/encoder?USER=<username>&PWD=<password>&Channel=1&SNAPSHOT
    ```

1. Configure BerryNet

    1. Edit `config.ipcameraSnapshot` in `/usr/local/berrynet/config.js`.
    2. Restart BerryNet.

# Get Nest Camera's Snapshot URL

Follow the [quick start guide](https://codelabs.developers.google.com/codelabs/wwn-api-quickstart/#0) to get snapshot URL. The high-level steps are:

1. Create a "product" (the concept is like a project, we will use it for personal usage).
1. Get access token from Nest cloud service.
1. Get snapshot URL with the access token Nest cloud service.
