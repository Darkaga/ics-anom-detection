# Phase 4 Monitoring & Testing Guide

## Overview

This guide provides comprehensive instructions for monitoring and testing the Phase 4 real-time detection system.

## Pre-Deployment Checklist

Before starting Phase 4, verify:

```bash
# 1. Check Phase 1 (ICSSIM) is running
make ot-status
# Expected: 6 containers running (2 PLCs, 3 HMIs, 1 Physical Sim)

# 2. Check Phase 2 (Collection) is running
docker ps | grep zeek
# Expected: zeek container running

# 3. Verify log files exist
ls -lh data/zeek/modbus_detailed-current.log
# Expected: File exists and is growing

# 4. Verify trained model exists
ls -lh data/models/anomaly_detector.pkl
# Expected: File exists, ~2-3 MB

# 5. Check network
docker network ls | grep ics-net
# Expected: ics-net bridge network exists
```

If any checks fail, fix those phases first before proceeding.

## Deployment Steps

### 1. Build Detection Container

```bash
make detection-build
```

**Expected output:**
```
Building detection API container...
[+] Building 45.2s (12/12) FINISHED
✓ Build complete
```

**Troubleshooting:**
- If build fails on pip install, check internet connectivity
- If COPY fails, ensure files exist in docker/detection/

### 2. Start Detection API

```bash
make detection-up
```

**Expected output:**
```
Starting real-time detection API...
[+] Running 1/1
 ✓ Container ics-detection-api  Started
✓ Detection API started

API Endpoints:
  - Health:        http://localhost:8000/health
  - Status:        http://localhost:8000/status
  ...
```

**Verification:**
```bash
# Check container is running
docker ps | grep detection
# Expected: ics-detection-api running on port 8000

# Check health
curl http://localhost:8000/health
# Expected: {"status":"healthy",...}
```

### 3. Monitor Initial Startup

```bash
make detection-logs
```

**Expected log sequence:**
```
INFO - Starting ICS Anomaly Detection API
INFO - Loading model from /data/models/anomaly_detector.pkl
INFO - Starting real-time detection engine
INFO - Monitoring: /data/zeek/modbus_detailed-current.log
INFO - Model: /data/models/anomaly_detector.pkl
INFO - Window: 300s, Poll: 5s
INFO - Detection engine started
INFO - Application startup complete.
INFO - Uvicorn running on http://0.0.0.0:8000
```

**Warning signs:**
- "Model not found" → Run `make ml-pipeline`
- "Log file not found" → Check Phase 2 collection
- Python tracebacks → Check container logs

## Monitoring During Operation

### Real-Time Log Monitoring

```bash
# Follow logs in real-time
make detection-logs

# Expected periodic messages (every 5 seconds):
# (If no new data, no output)

# When window completes (every 5 minutes):
INFO - Analyzing X device pairs from completed window
INFO - No anomalies detected in this window
# OR
WARNING - ANOMALY DETECTED: 192.168.0.21 → 192.168.0.11 (score: -0.682)
INFO - Saved X anomalies to /data/detections/anomalies_TIMESTAMP.parquet
```

### API Status Monitoring

```bash
# Quick status check
make detection-status

# Expected output:
{
  "status": "running",
  "detector_running": true,
  "started_at": "2025-11-08T10:00:00",
  "records_processed": 45230,
  "anomalies_detected": 3,
  "last_check": "2025-11-08T10:29:55",
  "current_window": 5875290
}
```

**Key metrics to monitor:**
- `records_processed`: Should increase over time
- `anomalies_detected`: May be 0 or small initially
- `last_check`: Should be recent (within last 10 seconds)
- `current_window`: Should increment every 5 minutes

### File System Monitoring

```bash
# Watch log file size
watch -n 5 'ls -lh data/zeek/modbus_detailed-current.log'

# Monitor detection output
watch -n 30 'ls -lh data/detections/'

# Check disk usage
du -sh data/detections/
```

**Expected growth rates:**
- Log file: ~500KB/minute (varies with traffic)
- Detection files: ~1MB/hour
- Total disk usage: ~50MB/day

## Testing API Endpoints

### Automated Test Suite

```bash
make detection-test
```

**Expected output:**
```
Testing detection API endpoints...

1. Health Check:
{
  "status": "healthy",
  "timestamp": "2025-11-08T10:30:00",
  "version": "1.0.0"
}

2. Status:
{
  "status": "running",
  "detector_running": true,
  ...
}

3. Recent Anomalies:
{
  "count": 2,
  "anomalies": [...]
}

4. Statistics:
{
  "total_anomalies": 5,
  "files": 2,
  ...
}
```

### Manual Endpoint Testing

#### 1. Health Check

```bash
curl http://localhost:8000/health
```

**Expected:** HTTP 200, JSON response with "healthy" status

#### 2. System Status

```bash
curl http://localhost:8000/status | jq
```

**Expected:** Current detector state with metrics

#### 3. Feature Information

```bash
curl http://localhost:8000/info/features | jq
```

**Expected:** List of 28 features with descriptions

#### 4. Current Anomalies

```bash
curl http://localhost:8000/anomalies/current?limit=10 | jq
```

**Expected:** 
- 0 anomalies initially (normal)
- 1-5 anomalies after 30+ minutes (depends on traffic patterns)

#### 5. Statistics

```bash
curl http://localhost:8000/anomalies/stats | jq
```

**Expected:** Aggregated stats across all detection files

#### 6. Historical Query

```bash
curl -X POST http://localhost:8000/anomalies/history \
  -H "Content-Type: application/json" \
  -d '{
    "start_time": "2025-11-08T00:00:00",
    "limit": 50
  }' | jq
```

**Expected:** Filtered anomaly results from Parquet files

### Interactive API Testing

Visit http://localhost:8000/docs for Swagger UI:

1. Click on any endpoint
2. Click "Try it out"
3. Enter parameters
4. Click "Execute"
5. View response

## Performance Testing

### Load Testing

```bash
# Install apache bench (if needed)
sudo apt-get install apache2-utils

# Test health endpoint (should handle 1000 req/s)
ab -n 1000 -c 10 http://localhost:8000/health

# Test status endpoint (should handle 100 req/s)
ab -n 500 -c 5 http://localhost:8000/status
```

**Expected results:**
- Health: <10ms average response time
- Status: <50ms average response time
- No failures (100% success rate)

### Latency Testing

```bash
# Measure end-to-end latency
time curl http://localhost:8000/status

# Expected: <100ms for local requests
```

## Validation Script

```bash
cd ~/ics-anom-demo
./scripts/validate_phase4.sh
```

**Expected output:**
```
=================================================
Phase 4: Real-Time Detection API Validation
=================================================

[1/8] Checking API availability...
✓ API is running

[2/8] Testing health endpoint
✓ Health check passed

[3/8] Testing status endpoint
✓ Detector is running

[4/8] Testing feature info endpoint
✓ Correct feature count (28)

[5/8] Testing current anomalies endpoint
Found X recent anomalies

[6/8] Testing statistics endpoint
✓ Statistics retrieved

[7/8] Testing historical query endpoint
Found X historical anomalies

[8/8] Checking data directories
✓ Model found: 2.5M
✓ Log file found: 487K (12345 lines)
Detection output files: 2

=================================================
Validation Summary
=================================================

Records Processed:    45230
Anomalies Detected:   3
API Status:           Running

✓ Phase 4 validation complete!
```

## Common Issues and Solutions

### Issue: API not responding

**Symptoms:**
```bash
curl http://localhost:8000/health
curl: (7) Failed to connect to localhost port 8000: Connection refused
```

**Diagnosis:**
```bash
docker ps | grep detection
# Is container running?

make detection-logs
# Check for startup errors
```

**Solutions:**
```bash
# Restart the service
make detection-restart

# If still failing, rebuild
make detection-down
make detection-build
make detection-up
```

### Issue: No records being processed

**Symptoms:**
- `records_processed: 0` in status
- Log file exists but no activity in API logs

**Diagnosis:**
```bash
# Check log file is growing
ls -lh data/zeek/modbus_detailed-current.log
sleep 60
ls -lh data/zeek/modbus_detailed-current.log
# File size should increase

# Check if Zeek is running
docker ps | grep zeek

# Check if ICSSIM is generating traffic
make ot-status
```

**Solutions:**
```bash
# If Zeek not running:
make collection-up

# If ICSSIM not running:
make ot-up

# Wait 5 minutes and check again
```

### Issue: High false positive rate

**Symptoms:**
- Hundreds of anomalies detected
- Most look like normal traffic

**Diagnosis:**
```bash
# Check anomaly scores
curl http://localhost:8000/anomalies/current?limit=20 | \
  jq '.anomalies[] | .anomaly_score'

# If many scores are close to -0.5, threshold is too lenient
```

**Solutions:**
```bash
# 1. Adjust threshold in compose file
nano compose/compose.detection.yaml
# Change: ANOMALY_THRESHOLD=-0.7  # More strict

# 2. Restart service
make detection-restart

# 3. Or retrain model with different contamination
# Edit scripts/train_model.py
# Change contamination parameter (default: 0.01)
make ml-pipeline
```

### Issue: Container keeps restarting

**Symptoms:**
```bash
docker ps -a | grep detection
# Container shows "Restarting" status
```

**Diagnosis:**
```bash
# Check logs for Python errors
docker logs ics-detection-api --tail 100
```

**Common causes:**
1. Model file missing
2. Import errors (missing dependencies)
3. Invalid configuration

**Solutions:**
```bash
# Rebuild with verbose output
docker compose -f compose/compose.detection.yaml build --no-cache

# Check model exists
ls -lh data/models/anomaly_detector.pkl

# Verify Python dependencies
docker compose -f compose/compose.detection.yaml run --rm detection-api pip list
```

## Continuous Monitoring Strategy

### Short-term (Every 5 minutes)

```bash
# Quick status check
curl -s http://localhost:8000/status | jq '.records_processed, .anomalies_detected'
```

### Medium-term (Every hour)

```bash
# Check for new anomalies
curl -s http://localhost:8000/anomalies/stats | jq '.total_anomalies'

# Check detection file count
ls data/detections/ | wc -l
```

### Long-term (Daily)

```bash
# Archive old detection files
cd data/detections
tar -czf archive_$(date +%Y%m%d).tar.gz anomalies_*.parquet
rm anomalies_*.parquet

# Check disk usage
du -sh data/detections/
```

## Automated Monitoring Script

Create `monitor-detection.sh`:

```bash
#!/bin/bash
# Continuous monitoring script

while true; do
    echo "=== $(date) ==="
    
    # Check API health
    if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "✓ API healthy"
    else
        echo "✗ API down - restarting"
        cd ~/ics-anom-demo
        make detection-restart
    fi
    
    # Get status
    STATUS=$(curl -s http://localhost:8000/status)
    RECORDS=$(echo $STATUS | jq -r '.records_processed')
    ANOMALIES=$(echo $STATUS | jq -r '.anomalies_detected')
    
    echo "Records: $RECORDS"
    echo "Anomalies: $ANOMALIES"
    
    # Alert on anomalies
    if [ $ANOMALIES -gt 0 ]; then
        LATEST=$(curl -s http://localhost:8000/anomalies/current?limit=1)
        echo "ALERT: Recent anomaly detected"
        echo $LATEST | jq '.anomalies[0]'
    fi
    
    echo ""
    sleep 300  # Check every 5 minutes
done
```

Run with:
```bash
chmod +x monitor-detection.sh
./monitor-detection.sh
```

## Success Criteria

Phase 4 is working correctly when:

✅ **API responds** to all endpoints without errors
✅ **Records are processed** (`records_processed` > 0 and increasing)
✅ **Windows are completing** (logs show "Analyzing X device pairs")
✅ **Detection files are created** (in `data/detections/`)
✅ **Status is current** (`last_check` within last 10 seconds)
✅ **No container restarts** (container uptime > 30 minutes)

## Next Steps

Once Phase 4 is validated and stable:

1. **Let it run for 24 hours** to collect baseline anomaly patterns
2. **Document normal anomaly rates** (how many anomalies per hour is normal?)
3. **Test with attack scenarios** (Phase 6)
4. **Build dashboard** (Phase 5) to visualize results
5. **Set up alerting** (Slack/email notifications)

## Support Resources

- **Quick Start:** `docs/PHASE4-QUICKSTART.md`
- **Full Documentation:** `docs/phase4-detection.md`
- **API Docs:** http://localhost:8000/docs
- **Validation Script:** `./scripts/validate_phase4.sh`
- **Project Status:** `make status`
