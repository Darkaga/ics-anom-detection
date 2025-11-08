# =============================================================================
# Zeek with ICSNPP-Modbus Plugin
# =============================================================================

FROM zeek/zeek:8.0.4

LABEL maintainer="ICS Anomaly Detection"
LABEL description="Zeek with ICSNPP-Modbus for ICS traffic analysis"
LABEL phase="2-collection"

USER root

# Install dependencies
RUN apt-get update && apt-get install -y \
    git \
    cmake \
    make \
    g++ \
    gcc \
    libssl-dev \
    python3 \
    python3-pip \
    curl \
    iproute2 \
    tcpdump \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies for MinIO upload
RUN pip3 install --no-cache-dir --break-system-packages \
    minio \
    watchdog

# Install ICSNPP-Modbus plugin using zkg
RUN echo "Y" | zkg autoconfig && \
    zkg refresh && \
    zkg install --force https://github.com/cisagov/icsnpp-modbus

# Create Zeek directories
RUN mkdir -p /zeek/logs /zeek/scripts /zeek/pcaps

# Create Zeek configuration - load ICSNPP-Modbus correctly
RUN echo '# Load ICSNPP-Modbus package' > /zeek/scripts/local.zeek && \
    echo '@load icsnpp-modbus' >> /zeek/scripts/local.zeek && \
    echo '# Output logs as JSON' >> /zeek/scripts/local.zeek && \
    echo 'redef LogAscii::use_json = T;' >> /zeek/scripts/local.zeek

# Create entrypoint script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Create upload script for MinIO
COPY upload_to_minio.py /usr/local/bin/upload_to_minio.py
RUN chmod +x /usr/local/bin/upload_to_minio.py

WORKDIR /zeek

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
