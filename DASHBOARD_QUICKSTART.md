# 🚀 Dashboard Quick Start - 5 Minutes to Your First Attack

## Prerequisites Check (30 seconds)

```bash
# Verify all services running
make status

# Should show:
# - Phase 1: ICSSIM (6 containers)
# - Phase 2: Collection (zeek + minio)
# - Phase 4: Detection API (1 container)
```

## Step 1: Build & Start (2 minutes)

```bash
# Build dashboard + attacker (first time only)
make dashboard-build

# Start both services
make dashboard-up

# Verify running
make dashboard-status
```

**Expected Output:**
```
✓ Dashboard started

Access dashboard at: http://localhost:8501
Attack API at: http://localhost:8002
Detection API at: http://localhost:8001
```

## Step 2: Open Dashboard (10 seconds)

Open your browser to: **http://localhost:8501**

You should see:
- 🟢 Green status indicators for both APIs
- System metrics (records processed, anomalies detected)
- Three tabs: Monitoring, Attack Control, Analytics

## Step 3: Execute First Attack (30 seconds)

1. Click **"Attack Control"** tab
2. Select attack type: **"Reconnaissance Scan"**
3. Select target: **"PLC1"**
4. Set duration: **30 seconds**
5. Click **"🚀 Launch Attack"**
6. You'll see: "✅ Attack launched: recon_scan_plc1_..."

## Step 4: Watch Detection (2 minutes)

1. Click **"Monitoring"** tab
2. Enable **"Auto-Refresh"** (should be on by default)
3. Set refresh interval to **10 seconds**
4. Wait 1-2 minutes for detection window to complete
5. Watch anomalies appear in the table!

**What to expect:**
- First anomalies appear 1-2 minutes after attack starts
- Anomaly scores between -0.6 and -0.4
- Source IP: 192.168.0.42 (attacker)
- Destination: 192.168.0.11 (PLC1)

## Step 5: Analyze Results (30 seconds)

1. Click **"Analytics"** tab
2. View total anomalies detected
3. See anomaly distribution by source/destination
4. Check score statistics

## 🎯 Try All Attack Types

Now repeat with different attacks to compare:

```bash
# Quick test from command line (optional)
docker exec ics-attacker python3 attacks/recon_scan.py 192.168.0.11 30
docker exec ics-attacker python3 attacks/unauthorized_write.py 192.168.0.11 30
docker exec ics-attacker python3 attacks/command_injection.py 192.168.0.11 30
docker exec ics-attacker python3 attacks/dos_flood.py 192.168.0.11 30
```

Or use the dashboard:
- **Reconnaissance Scan** → Detects in 1-2 minutes
- **Unauthorized Write** → Detects in 2-3 minutes
- **Command Injection** → Detects in 1-2 minutes
- **DoS Flood** → Detects in 1 minute (most aggressive)

## 🐛 Troubleshooting

### Dashboard won't load
```bash
docker logs ics-dashboard
make dashboard-restart
```

### APIs show red
```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
```

### No anomalies appear
- Wait 5-10 minutes for full detection window
- Try more aggressive attack (DoS Flood)
- Check detection logs: `make detection-logs`

## 📊 Understanding Results

**Anomaly Score Meaning:**
- `-0.3 to -0.1`: Normal baseline noise
- `-0.5 to -0.3`: Suspicious activity
- `-0.8 to -0.5`: Clear anomaly (attacks)
- `< -0.8`: Severe anomaly

**Detection Time:**
- Window size: 5 minutes
- First detection: 5-10 minutes after attack start
- Real-time updates: Every 10 seconds (dashboard refresh)

## 🎉 Success!

You now have:
✅ Interactive dashboard monitoring ICS traffic  
✅ One-click attack execution capability  
✅ Real-time anomaly detection visualization  
✅ Full attack scenario testing platform  

**Next:** Explore all attack types and compare detection patterns!

---

**Need help?** See [PHASE5_6_README.md](./PHASE5_6_README.md) for detailed documentation.
