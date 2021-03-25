# We start from Debian Buster. Can be rebase to Raspbian because they are
# similar
FROM python:3.7-slim-buster
LABEL maintainer="dev@dt42.io"
LABEL project="Berrynet"
LABEL version="3.7.0"

ENV POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR='/var/cache/pypoetry'

# Update apt
RUN apt-get update \
    # Install dependencies
    && apt-get install -y --no-install-recommends git sudo wget lsb-release software-properties-common gnupg \
    # Install build-essential
    build-essential curl \
    # Install systemd
    systemd systemd-sysv \
    # Install daemons
    mosquitto mosquitto-clients \
    apache2

# Install python dependencies
WORKDIR /app
COPY poetry.lock poetry.lock
COPY pyproject.toml pyproject.toml
# [WORKAROUND]: pip3 20.2.1 in 3.7 image would raise "ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE"
# REF: https://stackoverflow.com/questions/61551480/clean-docker-pip-install-results-in-error-these-packages-do-not-match-the-hashe
RUN pip3 install pip==20.0.2 \
    && pip3 install --no-cache-dir poetry \
    && poetry install --no-interaction --no-ansi --no-dev \
    # Cleaning poetry installation's cache for production:
    && rm -rf "$POETRY_CACHE_DIR" \
    && pip3 uninstall -yq poetry

# Install BerryNet
WORKDIR /app/BerryNet
COPY . .
RUN ./configure

# remote redundant packages
RUN apt-get remove --auto-remove --purge -y git wget lsb-release software-properties-common curl build-essential \
    && rm -rf /var/lib/apt/lists/*