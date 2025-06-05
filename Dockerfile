ARG BUILD_FROM
ARG BUILD_VERSION
ARG BUILD_ARCH
FROM $BUILD_FROM

# Set shell
SHELL ["/bin/sh", "-o", "pipefail", "-c"]

# Update package index
RUN apk update

# Install base Python and pip
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-setuptools \
    py3-wheel \
    jq

# Create and activate virtual environment
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt /app/

# Install Python requirements in the virtual environment
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the application
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
