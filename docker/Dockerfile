# BerryNet image for Raspberry Pi 4 and 5 (linux/arm64).
#
#     $ docker build -t berrynet -f docker/Dockerfile .
#     $ docker run -p 1883:1883 -p 3000:3000 -p 8080:8080 \
#           --device /dev/video0 berrynet
FROM debian:trixie-slim

LABEL maintainer="dev@dt42.io"
LABEL project="Berrynet"

# Install with the same script as on Raspberry Pi OS. The source is only
# mounted for the installation, the image keeps the installed venv.
RUN --mount=type=bind,source=.,target=/usr/src/berrynet,rw \
    cd /usr/src/berrynet \
    && BERRYNET_SKIP_PLATFORM_CHECK=1 ./configure \
    && rm -rf /var/lib/apt/lists/* /root/.cache

EXPOSE 1883 3000 8080

# No systemd in the container, so start mosquitto here.
CMD ["sh", "-c", "mkdir -p /run/mosquitto && chown mosquitto: /run/mosquitto && mosquitto -d -c /etc/mosquitto/mosquitto.conf && exec supervisord -n -c /etc/supervisor/supervisord.conf"]
