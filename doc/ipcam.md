# Setup General Purpose IP Camera

Steps to connect your IP camera to BerryNet:

1. Get stream URL of the IP camera.

    The [camera connection database](https://www.ispyconnect.com/sources.aspx) can generate stream URL if your IP camera is supported.

    Most IP cameras provide an RTSP stream, for example:

    ```
    rtsp://<username>:<password>@<ip-address>:554/<stream-path>
    ```

1. Configure BerryNet

    1. Add `--stream-src <stream-url>` to the `bn_camera` command in `/etc/supervisor/conf.d/berrynet-litert.conf`.
    2. Apply the change with `sudo supervisorctl update`.
