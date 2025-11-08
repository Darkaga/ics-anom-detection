# Phase 1 v2 - Quick Deployment Guide

## ⚡ 20-Minute Deployment

### Prerequisites
- Ubuntu 24.04.3 LTS
- Docker 28.5.1+
- Sudo access
- Internet connectivity

### Step 1: Stop v1 (2 minutes)
```bash
cd ~/ics-anom-demo
make ot-down

# Backup v1
cd ~
mv ics-anom-demo ics-anom-demo-v1-backup
```

### Step 2: Deploy v2 (2 minutes)
```bash
cd ~
# Extract ics-anom-demo-v2.tar.gz here
tar -xzf ics-anom-demo-v2.tar.gz
cd ics-anom-demo

# Setup
./scripts/setup.sh
```

### Step 3: Build (10-15 minutes)
```bash
make ot-build
```

**What's happening:**
- Building 6+ Docker images
- Cloning ICSSIM repository
- Installing Python dependencies (pymodbus, scapy, numpy, pandas)
- Copying source files to containers

☕ **Perfect time for coffee!**

### Step 4: Start (30 seconds)
```bash
make ot-up
```

**You should see:**
```
✓ ICSSIM started

Containers:
  - PLC1 (192.168.0.11) - Tank controller [Modbus server]
  - PLC2 (192.168.0.12) - Conveyor controller [Modbus server]
  - HMI1 (192.168.0.21) - Operator interface [Modbus client]
  - HMI2 (192.168.0.22) - Operator interface [Modbus client]
  - HMI3 (192.168.0.23) - Operator interface [Modbus client]
  - Physical Sim (192.168.1.31) - Process simulation
```

### Step 5: Validate (2 minutes)
```bash
./scripts/validate_phase1.sh
```

**Expected output:**
```
=== Phase 1: Real ICSSIM Stack Validation ===
✓ Docker is installed
✓ Docker Compose is available
✓ compose.ot.yaml exists
✓ .env file exists
✓ ICSSIM stack running (6 containers)
✓ Container icssim-plc1 running
✓ Container icssim-plc2 running
✓ Container icssim-hmi1 running
✓ Container icssim-hmi2 running
✓ Container icssim-hmi3 running
✓ Container icssim-pys running
✓ ot_network exists
✓ ot_physical exists
✓ PLC1 has correct IP: 192.168.0.11
✓ PLC2 has correct IP: 192.168.0.12
✓ PLC1 Modbus port (502) accessible from HMI1
✓ PLC2 Modbus port (502) accessible from HMI1
✓ PLC1 Python process running
✓ HMI1 Python process running
✓ PLC1 generating logs
✓ Real Modbus traffic detected (X packets)

Tests passed: 18/18
✓ Phase 1 validation PASSED
```

### Step 6: Verify Real Traffic (1 minute)
```bash
make ot-traffic
```

**You should see real Modbus packets:**
```
19:45:10.123456 192.168.0.21.47892 > 192.168.0.11.502: Modbus
19:45:10.123567 192.168.0.11.502 > 192.168.0.21.47892: Modbus Response
19:45:11.234567 192.168.0.22.38291 > 192.168.0.12.502: Modbus
19:45:11.234678 192.168.0.12.502 > 192.168.0.22.38291: Modbus Response
```

Press `Ctrl+C` to stop.

## ✅ Success!

If you see:
- ✅ 6 containers running
- ✅ All validation tests pass
- ✅ Real Modbus packets in tcpdump

**Phase 1 v2 is working!**

## 🎯 Quick Commands

```bash
# Status check
make ot-status

# View logs
make ot-logs

# Health check
make ot-test

# Individual container logs
make ot-logs-plc1
make ot-logs-hmi1

# Shell access
make ot-shell-plc1
make ot-shell-hmi1

# Stop
make ot-down

# Restart
make ot-down && make ot-up
```

## 🐛 Troubleshooting

### Build Fails
```bash
# Check internet connectivity
ping -c 3 github.com

# Retry with no cache
make clean
docker compose -f compose/compose.ot.yaml build --no-cache
```

### Containers Exit
```bash
# Check logs
docker logs icssim-plc1
docker logs icssim-hmi1

# Common: Source files not copied
docker exec icssim-plc1 ls -la /src/
```

### No Modbus Traffic
```bash
# Wait 60 seconds for initialization
sleep 60

# Check PLC listening
docker exec icssim-hmi1 nc -zv 192.168.0.11 502

# Check Python processes
docker exec icssim-plc1 pgrep -f python
docker exec icssim-hmi1 pgrep -f python
```

### Network Conflicts
```bash
# Remove old v1 network if still present
docker network rm ot_net

# Recreate v2 networks
make ot-down
make ot-up
```

## 📊 Resource Usage

**Expected:**
```
CONTAINER         CPU %    MEM USAGE
icssim-plc1       0.5%     25-30 MB
icssim-plc2       0.5%     25-30 MB
icssim-hmi1       0.3%     20-25 MB
icssim-hmi2       0.3%     20-25 MB
icssim-hmi3       0.3%     20-25 MB
icssim-pys        0.3%     25-30 MB
──────────────────────────────────
TOTAL            ~2.2%    ~150-180 MB
```

## 🚀 Next Steps

1. **Let it run for 24 hours** to verify stability
2. **Monitor occasionally:**
   ```bash
   make ot-status
   make ot-logs
   docker stats $(docker ps -q --filter "label=com.ics-anom.phase=1")
   ```
3. **When stable:** Ready for Phase 2 (Zeek + MinIO)!

## 📝 Notes

**What changed from v1:**
- v1: 1 container, fake logs, no traffic
- v2: 6 containers, real Modbus/TCP, ready for capture

**IP Addresses (DO NOT CHANGE):**
- ICS Network: 192.168.0.0/24
- Physical Process: 192.168.1.0/24
- These are hardcoded in ICSSIM source

**Networks:**
- `ot_network` (br_icsnet) - Capture point for Phase 2
- `ot_physical` (br_phynet) - Internal process simulation

---

**Total Time:** ~20 minutes  
**Difficulty:** Easy  
**Result:** Real ICS traffic for ML training! 🎯
