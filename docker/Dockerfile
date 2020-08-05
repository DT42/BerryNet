# We start from Debian Buster. Can be rebase to Raspbian because they are
# similar
FROM debian:buster
LABEL maintainer="dev@dt42.io"
LABEL project="Berrynet"
LABEL version="3.7.0"

ENV POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR='/var/cache/pypoetry'

# Update apt
RUN apt-get update \
    # Install dependencies
    && apt-get install -y --no-install-recommends git wget lsb-release software-properties-common \
    # Install build-essential
    build-essential curl \
    # Install systemd
    systemd systemd-sysv \
    # Install python
    python3 python3-dev \
    # Install python libs
    python3-wheel python3-setuptools python3-pip \
    python3-paho-mqtt python3-logzero python3-astor \
    python3-opengl python3-six python3-grpcio \
    python3-keras-applications python3-keras-preprocessing \
    python3-protobuf python3-termcolor python3-numpy \
    # Install daemons
    mosquitto mosquitto-clients \
    apache2

# Install python dependencies
WORKDIR /app
COPY poetry.lock poetry.lock
COPY pyproject.toml pyproject.toml

RUN pip3 install --no-cache-dir poetry \
    && poetry install --no-interaction --no-ansi --no-dev \
    # Cleaning poetry installation's cache for production:
    && rm -rf "$POETRY_CACHE_DIR" \
    && pip3 uninstall -yq poetry

# Install BerryNet
WORKDIR /app/BerryNet
COPY . .
RUN ./configure