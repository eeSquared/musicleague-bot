ARG BUILD_FROM
FROM $BUILD_FROM

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install required packages and build dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    git \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    cargo \
    openssl-dev

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt /app/

# Upgrade pip and install requirements
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel && \
    pip3 install --no-cache-dir -r requirements.txt

# Copy data
COPY . /app/

# Create data directory
RUN mkdir -p /data

# Set the script to be executable
RUN chmod a+x /app/run.sh

# Labels
LABEL \
    io.hass.name="Music League Bot" \
    io.hass.description="A Discord bot for running music leagues with submissions, voting, and leaderboards" \
    io.hass.version="${BUILD_VERSION}" \
    io.hass.type="addon" \
    io.hass.arch="${BUILD_ARCH}"

# Entry point
CMD [ "/app/run.sh" ]
