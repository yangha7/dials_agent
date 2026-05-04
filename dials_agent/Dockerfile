# DIALS AI Agent — Lightweight Container
#
# This container packages only the dials_agent Python application.
# DIALS itself must be available on the host and mounted into the container.
#
# Build:
#   docker build -t dials-agent .
#
# Run (interactive):
#   docker run -it --rm \
#     -v /path/to/dials/bin:/opt/dials/bin \
#     -v /path/to/data:/data \
#     -v /path/to/output:/output \
#     -e DATA_DIRECTORY=/data \
#     --env-file .env \
#     dials-agent -d /output
#
# Run (auto mode):
#   docker run -it --rm \
#     -v /path/to/dials/bin:/opt/dials/bin \
#     -v /path/to/data:/data \
#     -v /path/to/output:/output \
#     -e DATA_DIRECTORY=/data \
#     --env-file .env \
#     dials-agent -d /output --auto

FROM python:3.13-slim

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libhdf5-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the agent source code
COPY . /app/dials_agent_src/
RUN pip install --no-cache-dir -e /app/dials_agent_src/

# Add DIALS to PATH (mounted at runtime)
ENV PATH="/opt/dials/bin:${PATH}"

# Default working directory for DIALS output
RUN mkdir -p /output /data
WORKDIR /output

# Expose the DIALS agent as the entrypoint
ENTRYPOINT ["python", "-m", "dials_agent.cli"]
CMD ["-d", "/output"]
