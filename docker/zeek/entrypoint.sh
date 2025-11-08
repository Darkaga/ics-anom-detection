#!/bin/bash
# =============================================================================
# Zeek Entrypoint - Capture Modbus traffic and upload to MinIO
# =============================================================================

set -e

INTERFACE="${ZEEK_INTERFACE:-br_icsnet}"
FILTER="${ZEEK_FILTER:-net 192.168.0.0/24 and tcp port 502}"
LOG_DIR="/zeek/logs"
ROTATION_INTERVAL="${ROTATION_INTERVAL:-3600}"

echo "========================================="
echo "Zeek ICS Packet Capture"
echo "========================================="
echo "Interface: $INTERFACE"
echo "Filter: $FILTER"
echo "Log Directory: $LOG_DIR"
echo "Rotation Interval: ${ROTATION_INTERVAL}s"
echo "MinIO Endpoint: $MINIO_ENDPOINT"
echo "========================================="

# Wait for MinIO to be ready
echo "Waiting for MinIO..."
until curl -sf "$MINIO_ENDPOINT/minio/health/live" > /dev/null 2>&1; do
    echo "MinIO not ready, waiting..."
    sleep 5
done
echo "MinIO is ready!"

# Check if interface exists
if ! ip link show "$INTERFACE" > /dev/null 2>&1; then
    echo "ERROR: Interface $INTERFACE not found!"
    echo "Available interfaces:"
    ip link show
    exit 1
fi

echo "Interface $INTERFACE found!"

# Start MinIO upload watcher in background
echo "Starting MinIO upload watcher..."
python3 /usr/local/bin/upload_to_minio.py &
UPLOAD_PID=$!

# Start Zeek
echo "Starting Zeek capture on $INTERFACE..."
cd /zeek/logs

exec zeek -i "$INTERFACE" \
    -C \
    --no-checksums \
    -f "$FILTER" \
    /zeek/scripts/local.zeek \
    Log::default_rotation_interval=${ROTATION_INTERVAL}secs \
    2>&1 | tee /zeek/logs/zeek.log
