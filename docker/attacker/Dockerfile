FROM python:3.11-slim

WORKDIR /app

# Install network tools and Python dependencies
RUN apt-get update && apt-get install -y \
    iputils-ping \
    netcat-traditional \
    tcpdump \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --no-cache-dir \
    pymodbus==3.5.4 \
    fastapi==0.104.1 \
    uvicorn==0.24.0 \
    pydantic==2.5.0

# Copy attack scripts
COPY attacks/ /app/attacks/
COPY attack_server.py /app/

# Make scripts executable
RUN chmod +x /app/attacks/*.py

# Expose API port
EXPOSE 8002

# Run attack server by default
CMD ["python", "attack_server.py"]
