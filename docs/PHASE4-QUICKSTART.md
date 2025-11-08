# Phase 4 Quick Start Guide

## Prerequisites

Before starting Phase 4, ensure you have completed:

✅ **Phase 1:** ICSSIM running and generating Modbus traffic
✅ **Phase 2:** Zeek collecting logs to `data/zeek/modbus_detailed-current.log`
✅ **Phase 3:** Trained model saved to `data/models/anomaly_detector.pkl`

## Quick Start (5 minutes)

### 1. Build the Detection Container

```bash
cd ~/ics-anom-demo
make detection-build
```

This builds a FastAPI container with:
- Python 3.11
- FastAPI + Uvicorn
- Pandas, NumPy, scikit-learn
- PyArrow for Parquet I/O

### 2. Start the Detection API

```bash
make detection-up
```

The API will:
- Load your trained model from Phase 3
- Start monitoring the live Zeek log file
- Begin detecting anomalies in real-time
- Expose REST endpoints on port 8000

### 3. Verify It's Working

```bash
# Check container is running
docker ps | grep detection

# Check API health
curl http://localhost:8000/health

# View logs
make detection-logs
```

### 4. Monitor Anomalies

```bash
# Get system status
curl http://localhost:8000/status | jq

# Get recent anomalies
curl http://localhost:8000/anomalies/current | jq

# Get statistics
curl http://localhost:8000/anomalies/stats | jq
```

## API Endpoints Overview

### Core Monitoring

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/status` | GET | System status & metrics |
| `/anomalies/current` | GET | Recent anomalies (in-memory) |
| `/anomalies/history` | POST | Query historical anomalies |
| `/anomalies/stats` | GET | Detection statistics |
| `/info/features` | GET | Feature information |

### Interactive Documentation

FastAPI auto-generates beautiful API docs:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Command Reference

```bash
# Build & Deploy
make detection-build        # Build container
make detection-up           # Start API
make detection-down         # Stop API
make detection-restart      # Restart API

# Monitoring
make detection-logs         # View logs (follow mode)
make detection-status       # Quick status check
make detection-test         # Test all endpoints

# Maintenance
make detection-clean        # Clean detection output files
make status                 # Show all services status
```

## How It Works

### 1. Log Monitoring (Every 5 seconds)

```
Zeek writes → modbus_detailed-current.log
                        ↓
            Detection API reads new lines
                        ↓
            Parses JSON Modbus records
                        ↓
            Buffers in 5-minute windows
```

### 2. Feature Extraction (Every 5 minutes)

```
When window completes:
    ↓
Extract 28 behavioral features
    ↓
Aggregate register → device pairs
    ↓
Add temporal context (rolling baseline)
```

### 3. Anomaly Detection (Immediate)

```
Features → Scale (StandardScaler)
              ↓
         Isolation Forest
              ↓
    Prediction = -1? → ANOMALY!
              ↓
         Log + Save to Parquet
              ↓
    Update in-memory buffer for API
```

## Expected Behavior

### First 5 Minutes
- API starts and loads model ✓
- Begins monitoring log file ✓
- Buffers Modbus records ✓
- **No anomalies yet** (waiting for first complete window)

### After 5 Minutes
- First window completes
- Features extracted
- Model makes first predictions
- You should see either:
  - "No anomalies detected in this window" (normal)
  - "ANOMALY DETECTED: ..." (anomaly found!)

### After 30 Minutes
- 6 windows analyzed
- Temporal context established (rolling baselines)
- Detection accuracy improves
- Parquet files created in `data/detections/`

## Troubleshooting

### Problem: API won't start

**Error:** "Trained model not found"

**Solution:**
```bash
# Train the model first
make ml-pipeline
```

### Problem: No anomalies detected

**Possible causes:**

1. **Not enough data yet**
   - Wait 10-15 minutes for multiple windows
   - Check: `curl http://localhost:8000/status`

2. **ICSSIM not running**
   ```bash
   make ot-status
   # If not running:
   make ot-up
   ```

3. **Zeek not collecting**
   ```bash
   ls -lh data/zeek/modbus_detailed-current.log
   # Should be growing in size
   ```

### Problem: High false positive rate

**Adjust the anomaly threshold:**

Edit `compose/compose.detection.yaml`:
```yaml
environment:
  - ANOMALY_THRESHOLD=-0.7  # More strict (default: -0.5)
```

Then restart:
```bash
make detection-restart
```

### Problem: API timeout/slow

**Check logs for errors:**
```bash
make detection-logs

# Look for:
# - Python tracebacks
# - "Error reading log file"
# - "Error detecting anomalies"
```

## Viewing Results

### From Command Line

```bash
# Recent anomalies (last 10)
curl -s http://localhost:8000/anomalies/current?limit=10 | jq '.anomalies[]'

# Filter by source
curl -s http://localhost:8000/anomalies/current | \
  jq '.anomalies[] | select(.src == "192.168.0.21")'

# Get anomaly scores
curl -s http://localhost:8000/anomalies/current | \
  jq '.anomalies[] | {src, dst, score: .anomaly_score}'
```

### From Python

```python
import requests
import pandas as pd

# Get current anomalies
response = requests.get('http://localhost:8000/anomalies/current?limit=50')
data = response.json()

# Convert to DataFrame
df = pd.DataFrame(data['anomalies'])
print(df[['src', 'dst', 'anomaly_score', 'detected_at']])

# Query historical data
query = {
    "start_time": "2025-11-08T00:00:00",
    "limit": 100
}
response = requests.post('http://localhost:8000/anomalies/history', json=query)
historical = pd.DataFrame(response.json()['anomalies'])
```

### From Parquet Files

```python
import pandas as pd
from pathlib import Path

# Load all detection files
files = Path('data/detections').glob('anomalies_*.parquet')
dfs = [pd.read_parquet(f) for f in files]
all_anomalies = pd.concat(dfs, ignore_index=True)

# Analyze
print(f"Total anomalies: {len(all_anomalies)}")
print(all_anomalies.groupby(['src', 'dst']).size())
```

## Performance Tips

### For High Traffic Environments

1. **Increase poll interval** (reduces CPU):
   ```yaml
   - POLL_INTERVAL=10  # Check every 10s instead of 5s
   ```

2. **Adjust window size** (for faster/slower detection):
   ```yaml
   - WINDOW_SECONDS=600  # 10-minute windows
   ```

3. **Batch processing** (process multiple records at once):
   - Already optimized in code
   - Processes all new lines in each poll

### For Limited Storage

Parquet files are already compressed, but you can:

```bash
# Archive old detection files
cd data/detections
tar -czf archive_$(date +%Y%m%d).tar.gz anomalies_*.parquet
rm anomalies_*.parquet  # Keep only archive
```

## Integration Examples

### Slack Notifications (Future Enhancement)

```python
# Add to detector.py in _detect_anomalies method:
import requests

def send_slack_alert(anomaly):
    webhook_url = os.getenv('SLACK_WEBHOOK')
    message = {
        "text": f"🚨 Anomaly Detected!\n"
                f"Source: {anomaly['src']}\n"
                f"Destination: {anomaly['dst']}\n"
                f"Score: {anomaly['anomaly_score']:.3f}"
    }
    requests.post(webhook_url, json=message)
```

### Grafana Dashboard (Future Enhancement)

Configure Grafana to:
1. Query the REST API via JSON datasource
2. Display real-time anomaly count
3. Show timeline of detections
4. Alert on new anomalies

## What's Next?

With Phase 4 running, you have:
✅ Real-time anomaly detection
✅ REST API for monitoring
✅ Historical query capability
✅ Parquet storage for analytics

**Next:** Phase 5 - Build a Streamlit dashboard to visualize everything!

## Support

- View full docs: `docs/phase4-detection.md`
- Test the system: `scripts/validate_phase4.sh`
- Check all services: `make status`
- View logs: `make detection-logs`

## Summary

Phase 4 gives you a production-ready anomaly detection API that:
- Monitors live Modbus traffic 24/7
- Detects suspicious behavior in real-time
- Provides REST API for integration
- Stores results for historical analysis
- Scales to thousands of transactions per minute

The detection engine uses the same 28 features you trained on in Phase 3, ensuring consistency between training and inference. Anomalies are identified using Isolation Forest scoring, and results are immediately available via the API.
