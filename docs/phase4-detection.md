# Phase 4: Real-Time Detection & REST API

## Overview

Phase 4 implements real-time anomaly detection that continuously monitors live Modbus traffic and exposes detection results through a REST API. The system processes streaming data, extracts features in 5-minute windows, applies the trained Isolation Forest model, and provides instant anomaly alerts.

## Architecture

```
┌─────────────────────┐
│  Zeek IDS           │
│  modbus_detailed    │
│  -current.log       │
└──────────┬──────────┘
           │ writes
           ▼
┌─────────────────────────────────────┐
│  Detection Engine (detector.py)     │
│  ┌───────────────────────────────┐  │
│  │ RealtimeFeatureExtractor      │  │
│  │ - Buffers records in memory   │  │
│  │ - Extracts 28 features        │  │
│  │ - Maintains temporal context  │  │
│  └───────────┬───────────────────┘  │
│              │ features              │
│              ▼                       │
│  ┌───────────────────────────────┐  │
│  │ RealtimeDetector              │  │
│  │ - Applies scaler + model      │  │
│  │ - Detects anomalies           │  │
│  │ - Saves to Parquet            │  │
│  └───────────┬───────────────────┘  │
└──────────────┼───────────────────────┘
               │ anomalies
               ▼
    ┌──────────────────────┐
    │  FastAPI (api.py)    │
    │  REST Endpoints      │
    └──────────────────────┘
```

## Components

### 1. RealtimeFeatureExtractor (`detector.py`)

**Purpose:** Extract the same 28 behavioral features from streaming data as used during training.

**Key Features:**
- **Sliding Window Buffer:** Maintains in-memory buffer for current 5-minute window
- **Register-Level Analysis:** Groups data by (time_window, src, dst, address)
- **Feature Extraction:** Computes value patterns, read frequency, timing statistics
- **Temporal Context:** Maintains history of last 5 windows per device pair
- **Rolling Baselines:** Compares current behavior to recent history

**Extracted Features (28 total):**

1. **Value Statistics** (8 features):
   - `value_mean_mean`, `value_mean_std`, `value_mean_min`, `value_mean_max`
   - `value_std_mean`, `value_std_max`
   - `value_range_mean`, `value_range_max`

2. **Volatility Metrics** (2 features):
   - `value_changes_sum` - Total number of value changes
   - `value_change_rate_mean` - Rate of value changes

3. **Read Patterns** (4 features):
   - `read_count_sum` - Total reads in window
   - `read_rate_mean` - Average reads per second
   - `inter_read_mean_mean` - Average time between reads
   - `inter_read_std_mean` - Variability in read timing

4. **Anomaly Indicators** (5 features):
   - `outlier_count_sum` - Number of statistical outliers (>3σ)
   - `max_z_score_max` - Largest Z-score
   - `unique_values_mean` - Value diversity
   - `entropy_mean` - Value distribution entropy
   - `registers_accessed` - Number of unique registers

5. **Temporal Context** (9 features):
   - `value_mean_mean_rolling_mean` - Baseline for value patterns
   - `value_mean_mean_rolling_std` - Baseline variability
   - `value_mean_mean_deviation` - Deviation from baseline
   - `read_count_sum_rolling_mean` - Baseline for read frequency
   - `read_count_sum_rolling_std` - Read frequency variability
   - `read_count_sum_deviation` - Read frequency deviation
   - `value_change_rate_mean_rolling_mean` - Baseline volatility
   - `value_change_rate_mean_rolling_std` - Volatility variability
   - `value_change_rate_mean_deviation` - Volatility deviation

**Algorithm:**
```python
1. Monitor log file for new lines
2. Parse JSON records from each line
3. For each record:
   a. Determine time_window = floor(timestamp / 300)
   b. Buffer in memory: window_buffer[(window, src, dst, addr)]
   c. If window changed:
      - Extract features from completed window
      - Aggregate register-level → device-pair level
      - Add temporal context from history
      - Return features for detection
      - Update history for each device pair
      - Clear buffer and advance window
```

### 2. RealtimeDetector (`detector.py`)

**Purpose:** Apply trained model to detect anomalies in real-time.

**Key Features:**
- **Log Monitoring:** Tails `modbus_detailed-current.log` with configurable poll interval
- **Model Application:** Loads pre-trained Isolation Forest + StandardScaler
- **Anomaly Scoring:** Flags predictions = -1 with score < -0.5
- **Result Storage:** Saves anomalies to timestamped Parquet files
- **Status Tracking:** Maintains statistics for API queries

**Configuration (Environment Variables):**
```bash
LOG_FILE=/data/zeek/modbus_detailed-current.log
MODEL_PATH=/data/models/anomaly_detector.pkl
OUTPUT_DIR=/data/detections
WINDOW_SECONDS=300        # 5-minute windows
POLL_INTERVAL=5           # Check for new data every 5s
ANOMALY_THRESHOLD=-0.5    # Score threshold for alerts
LOG_LEVEL=INFO
```

**Detection Flow:**
```
1. Poll log file every POLL_INTERVAL seconds
2. Read new lines since last position
3. Parse JSON records
4. Add to FeatureExtractor buffer
5. When window completes:
   a. Extract 28 features
   b. Scale using trained scaler
   c. Predict using Isolation Forest
   d. Flag anomalies (prediction == -1)
   e. Log anomaly details
   f. Save to Parquet
   g. Update in-memory buffer for API
```

**Output Format (Parquet):**
```
anomalies_YYYYMMDD_HHMMSS.parquet
├── time_window (int)
├── src (str)
├── dst (str)
├── anomaly_score (float)
├── detected_at (ISO timestamp)
└── all 28 feature values
```

### 3. FastAPI REST API (`api.py`)

**Purpose:** Provide REST endpoints for monitoring and querying anomaly detection.

**Endpoints:**

#### GET `/health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-08T10:30:00",
  "version": "1.0.0"
}
```

#### GET `/status`
Get detection system status.

**Response:**
```json
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

#### GET `/anomalies/current?limit=20`
Get recent anomalies from memory (default: last 20).

**Response:**
```json
{
  "count": 2,
  "anomalies": [
    {
      "time_window": 5875290,
      "src": "192.168.0.21",
      "dst": "192.168.0.11",
      "anomaly_score": -0.682,
      "detected_at": "2025-11-08T10:25:00",
      "value_mean_mean": 4567.8,
      "read_count_sum": 142,
      "registers_accessed": 16
    }
  ]
}
```

#### POST `/anomalies/history`
Query historical anomalies from Parquet files with filtering.

**Request Body:**
```json
{
  "start_time": "2025-11-08T00:00:00",
  "end_time": "2025-11-08T12:00:00",
  "src": "192.168.0.21",
  "dst": "192.168.0.11",
  "min_score": -1.0,
  "limit": 100
}
```

**Response:** Same format as `/anomalies/current`

#### GET `/anomalies/stats`
Get anomaly detection statistics.

**Response:**
```json
{
  "total_anomalies": 15,
  "files": 3,
  "by_source": {
    "192.168.0.21": 8,
    "192.168.0.22": 5,
    "192.168.0.23": 2
  },
  "by_destination": {
    "192.168.0.11": 10,
    "192.168.0.12": 5
  },
  "score_distribution": {
    "min": -1.234,
    "max": -0.512,
    "mean": -0.748,
    "median": -0.695,
    "std": 0.198
  }
}
```

#### GET `/info/features`
Get information about the 28 features used in detection.

**Response:**
```json
{
  "num_features": 28,
  "window_seconds": 300,
  "features": ["value_mean_mean", "value_mean_std", ...],
  "description": "Behavioral features..."
}
```

## Deployment

### Prerequisites
- Phase 1 (ICSSIM) must be running
- Phase 2 (Zeek collection) must be running
- Phase 3 (Model training) must be complete with `anomaly_detector.pkl`

### Build and Start

```bash
# Build detection API container
make detection-build

# Start detection API (checks for trained model)
make detection-up

# View logs
make detection-logs

# Check status
make detection-status

# Test endpoints
make detection-test
```

### Directory Structure

```
data/
├── zeek/
│   └── modbus_detailed-current.log    # Input: Live log file
├── models/
│   └── anomaly_detector.pkl           # Input: Trained model
└── detections/
    └── anomalies_*.parquet            # Output: Detection results
```

## Performance Characteristics

- **Latency:** ~5 seconds (poll interval) from record write to detection
- **Throughput:** Processes ~4,000 Modbus transactions/minute
- **Window Size:** 5 minutes (300 seconds)
- **Feature Extraction:** ~1 second per completed window
- **Model Inference:** ~0.2 seconds per window
- **Memory:** ~500MB for buffers and history
- **Storage:** ~1MB per hour of Parquet files

## Monitoring

### Logs
```bash
# Real-time logs
make detection-logs

# Check container status
docker compose -f compose/compose.detection.yaml ps
```

### API Monitoring
```bash
# Health check
curl http://localhost:8000/health

# System status
curl http://localhost:8000/status

# Recent anomalies
curl http://localhost:8000/anomalies/current

# Statistics
curl http://localhost:8000/anomalies/stats
```

### Interactive API Documentation
FastAPI provides auto-generated interactive docs:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Troubleshooting

### "Detector not initialized"
- Check if model file exists: `ls -lh data/models/anomaly_detector.pkl`
- Run `make ml-pipeline` to train model

### "No anomalies detected"
- Verify ICSSIM is generating traffic: `make ot-status`
- Check Zeek is collecting logs: `ls -lh data/zeek/modbus_detailed-current.log`
- Monitor detection logs: `make detection-logs`
- Wait for at least 2-3 time windows (10-15 minutes)

### High false positive rate
- Adjust `ANOMALY_THRESHOLD` in compose file (default: -0.5)
- Retrain model with different contamination parameter
- Review detection logs for score distribution

### API not responding
```bash
# Check container is running
docker compose -f compose/compose.detection.yaml ps

# Check logs for errors
make detection-logs

# Restart service
make detection-restart
```

## Future Enhancements

1. **Alerting:**
   - Slack/email notifications
   - Webhook integrations
   - Syslog forwarding

2. **Model Management:**
   - Automatic retraining on schedule
   - A/B testing of models
   - Model versioning

3. **Advanced Analytics:**
   - Anomaly clustering
   - Root cause analysis
   - Attack pattern recognition

4. **Performance:**
   - GPU-accelerated inference
   - Batch processing optimization
   - Distributed detection for scale

## Security Considerations

- API has no authentication (add OAuth2/JWT for production)
- Read-only access to logs and models
- Results stored in separate directory
- Consider TLS for API endpoints in production
- Rate limiting not implemented (add for production)

## Integration Examples

### Python Client
```python
import requests

# Check status
response = requests.get('http://localhost:8000/status')
status = response.json()
print(f"Anomalies detected: {status['anomalies_detected']}")

# Get recent anomalies
response = requests.get('http://localhost:8000/anomalies/current?limit=10')
anomalies = response.json()

for anom in anomalies['anomalies']:
    print(f"Anomaly: {anom['src']} -> {anom['dst']}, score: {anom['anomaly_score']}")

# Query historical data
query = {
    "start_time": "2025-11-08T00:00:00",
    "src": "192.168.0.21",
    "limit": 50
}
response = requests.post('http://localhost:8000/anomalies/history', json=query)
results = response.json()
```

### Bash Monitoring Script
```bash
#!/bin/bash
# Monitor for new anomalies

while true; do
    STATUS=$(curl -s http://localhost:8000/status)
    COUNT=$(echo $STATUS | jq -r '.anomalies_detected')
    
    echo "$(date): Anomalies detected: $COUNT"
    
    if [ $COUNT -gt 0 ]; then
        LATEST=$(curl -s http://localhost:8000/anomalies/current?limit=1)
        echo $LATEST | jq -r '.anomalies[0]'
    fi
    
    sleep 60
done
```

## Next Steps

With Phase 4 complete, you can now:
1. **Monitor real-time anomalies** via API
2. **Query historical detections** from Parquet files
3. **Build dashboards** using the API endpoints
4. **Test attack scenarios** and validate detection

Ready for **Phase 5: Dashboard** to visualize detection results!
