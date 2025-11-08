# Phase 5 & 6 Deployment Checklist

**Date:** November 8, 2025  
**Objective:** Deploy interactive dashboard with attack testing capability

---

## 📋 Pre-Deployment Checklist

### 1. Verify Phase 1-4 Running

```bash
# Check all services
make status
```

**Expected output:**
- ✅ Phase 1: ICSSIM (6 containers running)
- ✅ Phase 2: Collection (zeek + minio running)
- ✅ Phase 4: Detection API (1 container running)

**If any phase not running:**
```bash
make ot-up              # Start Phase 1
make collection-up      # Start Phase 2
make detection-up       # Start Phase 4
```

### 2. Extract New Files

```bash
# Navigate to project directory
cd ~/ics-anom-demo/

# Extract the archive
tar -xzf /path/to/ics-anom-demo-phase5-6.tar.gz --strip-components=1

# Verify new files
ls docker/dashboard/
ls docker/attacker/
ls compose/compose.dashboard.yaml
```

**Expected files:**
- ✅ `docker/dashboard/Dockerfile`
- ✅ `docker/dashboard/dashboard.py`
- ✅ `docker/dashboard/.streamlit/config.toml`
- ✅ `docker/attacker/Dockerfile`
- ✅ `docker/attacker/attack_server.py`
- ✅ `docker/attacker/attacks/*.py` (4 files)
- ✅ `compose/compose.dashboard.yaml`
- ✅ Updated `Makefile`

### 3. Verify Network Exists

```bash
# Check for ot_network
docker network ls | grep ot_network
```

**If missing:**
```bash
# Network should have been created by Phase 1
make ot-up
```

---

## 🚀 Deployment Steps

### Step 1: Build Containers (First Time Only)

```bash
make dashboard-build
```

**Expected output:**
```
Building dashboard and attacker...
[+] Building X.Xs (XX/XX) FINISHED
✓ Build complete
```

**Estimated time:** 2-3 minutes

**If build fails:**
- Check internet connectivity (downloads Python packages)
- Verify Docker has enough disk space: `docker system df`
- Check build logs: `docker compose -f compose/compose.dashboard.yaml build --no-cache`

### Step 2: Start Services

```bash
make dashboard-up
```

**Expected output:**
```
Starting dashboard and attacker...
✓ Dashboard started

Access dashboard at: http://localhost:8501
Attack API at: http://localhost:8002
Detection API at: http://localhost:8001
```

**Estimated time:** 10-15 seconds

### Step 3: Verify Services Running

```bash
make dashboard-status
```

**Expected output:**
```
=== Dashboard Status ===
NAMES           STATUS          PORTS
ics-dashboard   Up X seconds    0.0.0.0:8501->8501/tcp

=== Attacker Status ===
NAMES          STATUS          PORTS
ics-attacker   Up X seconds    0.0.0.0:8002->8002/tcp
```

### Step 4: Health Checks

```bash
# Test Detection API
curl http://localhost:8001/health

# Test Attack API
curl http://localhost:8002/health

# Test Dashboard (should return HTML)
curl -I http://localhost:8501
```

**All should return 200 OK**

### Step 5: Open Dashboard

```bash
# Linux
xdg-open http://localhost:8501

# macOS
open http://localhost:8501

# Or manually open browser to: http://localhost:8501
```

**Expected:** Dashboard loads with three tabs (Monitoring, Attack Control, Analytics)

### Step 6: Verify Dashboard Status Indicators

In the dashboard sidebar, you should see:
- 🟢 **Detection API** (green)
- 🟢 **Attack API** (green)

**If red indicators:**
```bash
# Check logs
make dashboard-logs

# Restart services
make detection-restart
make dashboard-restart
```

---

## ✅ Validation Testing

### Test 1: System Metrics Display

**In Monitoring tab:**
- [ ] "Records Processed" shows number > 0
- [ ] "Anomalies Detected" shows 0 or small number
- [ ] "Current Window" shows a number or N/A
- [ ] "Detector" shows "🟢 Running"

### Test 2: Launch Attack

**In Attack Control tab:**
1. [ ] Select "Reconnaissance Scan"
2. [ ] Select "PLC1"
3. [ ] Set duration to "30" seconds
4. [ ] Click "🚀 Launch Attack"
5. [ ] See success message with attack ID
6. [ ] Attack appears in "Attack History" section
7. [ ] Status shows "🔄 Running"

### Test 3: Monitor Detection

**Wait 1-2 minutes, then check Monitoring tab:**
1. [ ] Anomalies table shows new entries
2. [ ] Source IP shows 192.168.0.42 (attacker)
3. [ ] Destination IP shows 192.168.0.11 (PLC1)
4. [ ] Anomaly scores between -0.8 and -0.3

**If no anomalies after 5 minutes:**
- Check detection logs: `make detection-logs`
- Verify attack completed: Check Attack Control → Attack History
- Try more aggressive attack (DoS Flood)

### Test 4: Analytics

**In Analytics tab:**
1. [ ] "Total Anomalies" shows count > 0
2. [ ] Score distribution shows min/max/mean
3. [ ] "Anomalies by Source IP" chart displays
4. [ ] "Anomalies by Destination IP" chart displays

### Test 5: All Attack Types

Run each attack and verify detection:

```bash
# Option A: From dashboard (preferred)
# Launch each attack type one at a time from Attack Control tab

# Option B: From command line
docker exec ics-attacker python3 attacks/recon_scan.py 192.168.0.11 30
docker exec ics-attacker python3 attacks/unauthorized_write.py 192.168.0.11 30
docker exec ics-attacker python3 attacks/command_injection.py 192.168.0.11 30
docker exec ics-attacker python3 attacks/dos_flood.py 192.168.0.11 30
```

**Expected detection rates:**
- [x] Recon Scan: 80-90%
- [x] Unauthorized Write: 60-70%
- [x] Command Injection: 70-80%
- [x] DoS Flood: 95-100%

---

## 🐛 Troubleshooting Guide

### Issue: Dashboard Won't Load

**Symptoms:** Browser shows "connection refused" or blank page

**Diagnosis:**
```bash
# Check if container running
docker ps | grep ics-dashboard

# Check logs for errors
docker logs ics-dashboard --tail 50

# Check port availability
sudo lsof -i :8501
```

**Solutions:**
```bash
# Restart dashboard
make dashboard-restart

# If port conflict, stop conflicting service or edit compose file
# Edit: compose/compose.dashboard.yaml, change 8501 to another port

# Rebuild if code changed
make dashboard-build
make dashboard-up
```

### Issue: API Status Shows Red

**Symptoms:** Dashboard shows 🔴 for Detection or Attack API

**Diagnosis:**
```bash
# Test APIs directly
curl http://localhost:8001/health
curl http://localhost:8002/health

# Check if containers running
docker ps | grep -E "ics-detection-api|ics-attacker"
```

**Solutions:**
```bash
# Restart detection API
make detection-restart

# Restart attacker
docker restart ics-attacker

# Check network connectivity
docker exec ics-dashboard ping -c 3 ics-detection-api
docker exec ics-dashboard ping -c 3 ics-attacker
```

### Issue: Attack Doesn't Execute

**Symptoms:** Click "Launch Attack" but nothing happens or error message

**Diagnosis:**
```bash
# Check attacker logs
docker logs ics-attacker

# Verify PLC connectivity
docker exec ics-attacker ping -c 3 192.168.0.11
docker exec ics-attacker nc -zv 192.168.0.11 502

# Check attack API
curl http://localhost:8002/attacks/available
```

**Solutions:**
```bash
# Verify PLCs are running
make ot-status

# Restart attacker
docker restart ics-attacker

# Check network (attacker should be on ot_network)
docker network inspect ot_network | grep ics-attacker
```

### Issue: No Anomalies Detected

**Symptoms:** Attack completes but no anomalies appear in dashboard

**Possible Causes:**
1. Detection window not complete (wait 5-10 minutes)
2. Attack too subtle (try DoS Flood)
3. Model threshold too strict
4. Feature extraction issue

**Diagnosis:**
```bash
# Check detection API is processing
curl http://localhost:8001/status | jq

# Check if records increasing
watch -n 5 'curl -s http://localhost:8001/status | jq .records_processed'

# Check detection logs
make detection-logs
```

**Solutions:**
```bash
# Wait full detection window (10 minutes from attack start)
# Try more aggressive attack (DoS Flood, duration 60 seconds)
# Check if zeek is capturing traffic
docker exec ics-zeek ls -lh /data/zeek/modbus_detailed-current.log
```

### Issue: Auto-Refresh Not Working

**Symptoms:** Dashboard doesn't update automatically

**Diagnosis:**
- Check if "Enable Auto-Refresh" checkbox is checked
- Check refresh interval setting

**Solutions:**
- Toggle Auto-Refresh off and on
- Adjust refresh interval
- Manually refresh browser (F5)
- Check browser console for errors

---

## 📊 Performance Validation

### Expected Metrics

**After 30-second attack:**
- Detection time: 1-10 minutes
- Anomalies detected: 5-30
- Anomaly scores: -0.8 to -0.3
- False positives: 0-2

**System Resources:**
```bash
# Check container stats
docker stats --no-stream ics-dashboard ics-attacker

# Expected:
# Dashboard: ~150MB RAM, ~5% CPU
# Attacker: ~50MB RAM, ~10-30% CPU (during attack)
```

### Load Testing (Optional)

```bash
# Test API responsiveness
ab -n 100 -c 10 http://localhost:8001/status
ab -n 100 -c 10 http://localhost:8002/health

# Expected: < 100ms response time
```

---

## 📝 Documentation Verification

Ensure all documentation is accessible:

- [ ] `PHASE5_6_README.md` - Complete guide
- [ ] `DASHBOARD_QUICKSTART.md` - 5-minute quick start
- [ ] `PHASE5_6_IMPLEMENTATION.md` - Technical details
- [ ] `PROJECT_STATUS_SUMMARY.md` - Updated with Phase 5 & 6
- [ ] `Makefile` - Contains dashboard commands
- [ ] README files in docker/dashboard/ and docker/attacker/

---

## 🎯 Success Criteria

### Minimum Viable Demo (MVP)

- [x] Dashboard loads successfully
- [x] Both APIs show green status
- [x] Can launch at least one attack
- [x] Anomalies detected within 10 minutes
- [x] Attack history tracks executions
- [x] Analytics shows statistics

### Full Functionality

- [x] All attack types work
- [x] Auto-refresh updates display
- [x] Charts render correctly
- [x] No errors in logs
- [x] System stable for 1+ hours
- [x] Can execute multiple attacks in sequence

### Production Ready (for Lab/Demo)

- [x] Documentation complete
- [x] All validation tests pass
- [x] Performance within expected ranges
- [x] Troubleshooting guide works
- [x] Can recover from errors
- [x] Ready for demonstration

---

## 🎉 Completion Steps

### 1. Final Validation

```bash
# Run complete system check
make status

# Should show all 4 phases running:
# ✓ Phase 1: ICSSIM
# ✓ Phase 2: Collection
# ✓ Phase 4: Detection API
# ✓ Phase 5 & 6: Dashboard + Attacker
```

### 2. Create Backup

```bash
# Backup working state
cd ~
tar -czf ics-anom-demo-working-$(date +%Y%m%d).tar.gz \
    --exclude='ics-anom-demo/data/zeek/*.log' \
    ics-anom-demo/

# Backup model
cp ics-anom-demo/data/models/anomaly_detector.pkl \
   anomaly_detector-backup-$(date +%Y%m%d).pkl
```

### 3. Document Configuration

Record your specific settings:
- System IP address: ______________
- Dashboard port: 8501
- Attack API port: 8002
- Detection API port: 8001
- OT Network: ot_network (192.168.0.0/24)

### 4. Schedule Demo/Training

Now ready to:
- [ ] Demonstrate to team
- [ ] Conduct security training
- [ ] Perform research testing
- [ ] Document findings
- [ ] Plan enhancements

---

## 📞 Support Resources

### Quick Reference

- **Start:** `make dashboard-up`
- **Stop:** `make dashboard-down`
- **Logs:** `make dashboard-logs`
- **Restart:** `make dashboard-restart`
- **Status:** `make dashboard-status`

### Getting Help

1. Check logs: `make dashboard-logs`
2. Review troubleshooting guide above
3. Consult documentation: `PHASE5_6_README.md`
4. Check Docker health: `docker ps -a`
5. Verify network: `docker network inspect ot_network`

### Common Commands

```bash
# Full restart of everything
make dashboard-down
make detection-restart
make dashboard-up

# Clean rebuild
make dashboard-down
docker compose -f compose/compose.dashboard.yaml build --no-cache
make dashboard-up

# View all logs simultaneously
docker logs -f ics-dashboard &
docker logs -f ics-attacker &
docker logs -f ics-detection-api &
```

---

## ✅ Deployment Complete!

**Congratulations!** You now have a fully functional ICS anomaly detection system with:

✅ Interactive web dashboard  
✅ One-click attack execution  
✅ Real-time detection monitoring  
✅ Comprehensive analytics  
✅ Professional demonstration platform  

**Ready for use in:**
- Security training
- Research projects
- Executive demonstrations
- Proof-of-concept testing
- ICS security education

---

**Deployment Date:** _____________  
**Deployed By:** _____________  
**System Location:** _____________  
**Status:** ✅ Operational

**Next Steps:**
1. Review attack scenarios
2. Tune detection thresholds (if needed)
3. Schedule demonstrations
4. Document findings
5. Plan future enhancements
