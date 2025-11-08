# Phase 2: Collection Layer - Deployment Guide

## Overview

Phase 2 captures Modbus/TCP traffic from Phase 1, parses it with Zeek (including ICSNPP-Modbus plugin), and stores structured logs in MinIO for analysis.

## Prerequisites

- ✅ Phase 1 (OT layer) running and stable
- ✅ Real Modbus traffic flowing on br_icsnet
- ✅ Docker and Docker Compose available
- ✅ Ports 9000-9001 available for MinIO

## Quick Start

```bash
# 1. Build Phase 2
make collect-build

# 2. Start Phase 2
make collect-up

# 3. Validate
./scripts/validate_phase2.sh

# 4. Access MinIO Console
open http://localhost:9001
# Login: admin / minio123secure (or values from .env)
```

## What Gets Deployed

### 1. MinIO (S3-Compatible Storage)
- **Container:** `minio`
- **Ports:** 
  - 9000 (S3 API)
  - 9001 (Web Console)
- **Buckets:**
  - `pcaps` - Raw packet captures
  - `zeek-logs` - Parsed Zeek logs
  - `zeek-features` - Extracted features (Phase 3)
  - `models` - Trained ML models (Phase 4)

### 2. Zeek (Network Analysis)
- **Container:** `zeek`
- **Function:** Captures from `br_icsnet`, parses Modbus protocol
- **Plugin:** ICSNPP-Modbus for ICS-specific analysis
- **Output:** JSON-formatted logs rotated hourly

## Architecture

```
Phase 1 (OT Network)
  └─ br_icsnet bridge
       ↓ (packet capture)
Phase 2 (Collection)
  ├─ Zeek
  │   ├─ Captures packets
  │   ├─ Parses Modbus protocol
  │   └─ Generates structured logs
  └─ MinIO
      └─ Stores logs in zeek-logs bucket
```

## Verification

### Check Services
```bash
make collect-status
```

Expected output:
```
NAMES    STATUS           PORTS
zeek     Up X minutes     
minio    Up X minutes     0.0.0.0:9000-9001->9000-9001/tcp
```

### Check Zeek is Capturing
```bash
docker logs zeek | tail -20
```

Should see:
```
Interface br_icsnet found!
Starting Zeek capture on br_icsnet...
```

### Check MinIO Buckets
```bash
docker exec minio mc ls minio/
```

Should see:
```
[DATE] pcaps/
[DATE] zeek-logs/
[DATE] zeek-features/
[DATE] models/
```

### View Zeek Logs
```bash
docker exec minio mc ls minio/zeek-logs/
```

## MinIO Console

**Access:** http://localhost:9001

**Default Credentials:**
- Username: `admin`
- Password: `minio123secure`

**Change in** `.env`:
```bash
MINIO_ROOT_USER=your_username
MINIO_ROOT_PASSWORD=your_secure_password
```

## Zeek Log Format

Zeek outputs JSON logs with Modbus-specific fields:

```json
{
  "ts": 1699564800.123456,
  "uid": "CHhAvVGS1DHFjwGM9",
  "id.orig_h": "192.168.0.21",
  "id.orig_p": 47892,
  "id.resp_h": "192.168.0.11",
  "id.resp_p": 502,
  "proto": "tcp",
  "modbus": {
    "function": "read_holding_registers",
    "address": 0,
    "quantity": 10
  }
}
```

## Data Flow

1. **Capture:** Zeek captures packets from br_icsnet
2. **Parse:** ICSNPP-Modbus plugin extracts Modbus details
3. **Rotate:** Logs rotate every hour (configurable)
4. **Upload:** Watcher uploads rotated logs to MinIO
5. **Store:** Logs stored in MinIO with date hierarchy

## Configuration

### Rotation Interval

Change in `.env`:
```bash
ROTATION_INTERVAL=3600  # Seconds (default: 1 hour)
```

### Capture Filter

Modify in `compose.collection.yaml`:
```yaml
- ZEEK_FILTER=net 192.168.0.0/24 and tcp port 502
```

## Troubleshooting

### Zeek Can't Find Interface
```bash
# Check if br_icsnet exists
docker exec zeek ip link show br_icsnet

# If not, check Phase 1 is running
make ot-status
```

### No Logs Being Generated
```bash
# Check Zeek is capturing
docker exec zeek tcpdump -i br_icsnet -nn 'tcp port 502' -c 5

# Check Zeek process
docker exec zeek pgrep -f zeek
```

### MinIO Connection Issues
```bash
# Check MinIO health
curl http://localhost:9000/minio/health/live

# Check logs
docker logs minio
```

### Logs Not Uploading to MinIO
```bash
# Check upload script
docker logs zeek | grep -i upload

# Check MinIO credentials
docker exec zeek env | grep MINIO
```

## Commands Reference

```bash
# Build
make collect-build

# Start/Stop
make collect-up
make collect-down

# Status
make collect-status
make collect-test

# Logs
make collect-logs           # All logs
make collect-logs-zeek      # Zeek only
make collect-logs-minio     # MinIO only

# Validation
./scripts/validate_phase2.sh
```

## Storage Management

### Check Bucket Size
```bash
docker exec minio mc du minio/zeek-logs
```

### List Recent Logs
```bash
docker exec minio mc ls minio/zeek-logs/$(date +%Y/%m/%d)/
```

### Download Logs
```bash
docker exec minio mc cp minio/zeek-logs/2024/11/08/ ./data/zeek/ --recursive
```

## Next Steps

Once Phase 2 is collecting data (recommended: 24 hours of logs):

**Phase 3: Featurization**
- Extract features from Zeek logs
- Create time-windowed feature vectors
- Prepare data for ML training

## Success Criteria

Phase 2 is ready for Phase 3 when:
- ✅ Zeek capturing continuously
- ✅ Logs rotating hourly
- ✅ MinIO receiving uploads
- ✅ 24+ hours of Modbus logs collected
- ✅ No container restarts or errors

---

**Phase 2: Capturing and storing real ICS traffic!** 📦
