# ICS Anomaly Detection - Phase 1 v2 (Real ICSSIM Stack)

Production-quality OT/ICS anomaly detection prototype using **real Modbus/TCP traffic** from authentic ICS simulation.

## 🎯 What's Different in v2

**v1 → v2 Upgrade:**
- ❌ v1: Single container with fake traffic logs
- ✅ v2: 6+ containers with **real Modbus/TCP packets**
- ✅ Authentic bottle-filling factory simulation
- ✅ Ready for Zeek packet capture in Phase 2

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│           ot_network (192.168.0.0/24)                        │
│              Real Modbus/TCP on Port 502                      │
│                                                               │
│   ┌─────────┐  ┌─────────┐       ┌──────────┐              │
│   │  PLC1   │  │  PLC2   │       │ Attacker │              │
│   │ .0.11   │  │ .0.12   │       │  .0.42   │              │
│   │[SERVER] │  │[SERVER] │       │ [ATTACK] │              │
│   └────▲────┘  └────▲────┘       └──────────┘              │
│        │            │                                        │
│        │ Modbus     │ Modbus                                │
│        │ Req/Resp   │ Req/Resp                              │
│        │            │                                        │
│   ┌────▼────┐  ┌───▼─────┐  ┌──────────┐                  │
│   │  HMI1   │  │  HMI2   │  │   HMI3   │                  │
│   │  .0.21  │  │  .0.22  │  │   .0.23  │                  │
│   │[CLIENT] │  │[CLIENT] │  │ [CLIENT] │                  │
│   └─────────┘  └─────────┘  └──────────┘                  │
│                                                               │
└──────────────────────────────────────────────────────────────┘
                           │
                           │ Shared Memory
                           ▼
┌──────────────────────────────────────────────────────────────┐
│         ot_physical (192.168.1.0/24)                         │
│                                                               │
│   ┌────────────────────────────────────────────────────┐    │
│   │      Physical Simulation (192.168.1.31)            │    │
│   │  - Water tank (level control)                      │    │
│   │  - Conveyor belt (bottle transport)                │    │
│   │  - Filling process (bottle filling)                │    │
│   └────────────────────────────────────────────────────┘    │
│            ▲                                ▲                 │
│            │ Process I/O                    │ Process I/O     │
│       ┌────┴────┐                      ┌────┴────┐           │
│       │  PLC1   │                      │  PLC2   │           │
│       │ (.1.11) │                      │ (.1.12) │           │
│       └─────────┘                      └─────────┘           │
└──────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# 1. Setup
./scripts/setup.sh

# 2. Build (10-15 minutes)
make ot-build

# 3. Start
make ot-up

# 4. Validate
./scripts/validate_phase1.sh

# 5. Monitor real Modbus traffic!
make ot-traffic
```

## Current Status

```
Phase 1: OT Simulator          ✅ Real ICSSIM Stack (v2)
Phase 2: Collection Layer      ⏳ Next (Zeek + MinIO)
Phase 3: Featurization         ⏳ Coming
Phase 4: ML Models             ⏳ Coming
Phase 5: Dashboard             ⏳ Coming
Phase 6: Attack Scenarios      ⏳ Coming
```

## What You Get

### Components (6+ containers)

1. **PLC1** (192.168.0.11:502)
   - Tank level controller
   - Modbus server
   - Controls input/output valves
   
2. **PLC2** (192.168.0.12:502)
   - Conveyor controller
   - Modbus server
   - Controls belt motor

3. **HMI1, HMI2, HMI3** (192.168.0.21-23)
   - Operator interfaces
   - Modbus clients
   - Read/write to PLCs

4. **Physical Simulation** (192.168.1.31)
   - Bottle filling process
   - Tank simulation
   - Conveyor belt physics

5. **Attacker** (192.168.0.42) - Optional
   - Attack scenario container
   - Starts with `--profile attack`
   - For Phase 6 testing

### Real Traffic Generated

**Modbus Function Codes:**
- `0x03` - Read Holding Registers (tank level, valve status)
- `0x10` - Write Multiple Registers (valve commands, motor control)
- `0x01` - Read Coils (discrete status)
- `0x05` - Write Single Coil (on/off commands)

**Traffic Pattern:**
- HMIs poll PLCs every 1-5 seconds
- PLCs respond with process values
- ~10-50 Modbus transactions per minute
- Continuous operation 24/7

## Commands

### Basic Operations
```bash
make ot-build          # Build all containers
make ot-up             # Start ICSSIM stack
make ot-down           # Stop stack
make ot-status         # Show container status
make ot-test           # Health check
```

### Monitoring
```bash
make ot-logs           # All logs
make ot-logs-plc1      # PLC1 only
make ot-logs-hmi1      # HMI1 only
make ot-traffic        # Live Modbus packet capture
```

### Debugging
```bash
make ot-shell-plc1     # Shell into PLC1
make ot-shell-hmi1     # Shell into HMI1
```

### With Attacker
```bash
make ot-up-with-attacker    # Include attacker container
```

## Validation

Run full validation:
```bash
./scripts/validate_phase1.sh
```

Expected results:
- ✅ 6 containers running
- ✅ Networks created (ot_network, ot_physical)
- ✅ PLCs listening on port 502
- ✅ HMIs can connect to PLCs
- ✅ Real Modbus traffic detected
- ✅ Python processes active

## Verification

### Check Real Traffic
```bash
# Monitor Modbus packets
make ot-traffic

# You should see:
192.168.0.21.xxxxx > 192.168.0.11.502: Modbus Read Holding Registers
192.168.0.11.502 > 192.168.0.21.xxxxx: Modbus Response [Data]
```

### Test Connectivity
```bash
# From HMI1, test PLC connectivity
docker exec icssim-hmi1 nc -zv 192.168.0.11 502
docker exec icssim-hmi1 nc -zv 192.168.0.12 502
```

### View Logs
```bash
# PLC1 should show Modbus server activity
docker logs icssim-plc1

# HMI1 should show Modbus client requests
docker logs icssim-hmi1
```

## System Requirements

- Ubuntu 24.04+ LTS
- Docker 28.5.1+
- 64GB RAM (minimum 16GB)
- GPU optional (for Phase 4)
- 1TB+ SSD storage

## Network Configuration

**DO NOT CHANGE** these subnets - they're hardcoded in ICSSIM:
- `ot_network`: 192.168.0.0/24 (ICS network)
- `ot_physical`: 192.168.1.0/24 (Physical process)

For Phase 2+ collection:
- `collect_net`: 172.21.0.0/24
- `ml_net`: 172.22.0.0/24

## Troubleshooting

### Containers Exit Immediately
```bash
docker logs icssim-plc1
# Check for Python errors
```

### No Modbus Traffic
```bash
# Verify PLCs are listening
docker exec icssim-hmi1 nc -zv 192.168.0.11 502

# Check source files copied
docker exec icssim-plc1 ls -la /src/
```

### Network Conflicts
```bash
# If you have v1 still running
cd ~/ics-anom-demo && make ot-down

# Remove old networks
docker network rm ot_net
```

## Migration from v1

See **TRANSITION_FROM_V1.md** for detailed migration guide.

Quick migration:
```bash
# Stop v1
cd ~/ics-anom-demo && make ot-down

# Backup v1
cd ~ && mv ics-anom-demo ics-anom-demo-v1-backup

# Deploy v2
cd ics-anom-demo
./scripts/setup.sh
make ot-build
make ot-up
```

## Documentation

- `README.md` - This file
- `docs/phase1-v2.md` - Detailed technical guide
- `TRANSITION_FROM_V1.md` - Migration guide
- `.env.example` - Configuration reference

## Next Steps

Once Phase 1 v2 is stable (24+ hours):

**Phase 2: Collection Layer**
- Zeek with ICSNPP-Modbus plugin
- Capture from `br_icsnet` bridge
- Parse Modbus protocol details
- Store in MinIO (S3-compatible)

## Success Criteria

Phase 1 v2 is complete when:
- ✅ All 6 containers running continuously
- ✅ Modbus traffic visible in tcpdump
- ✅ No container restarts or errors
- ✅ Stable for 24+ hours
- ✅ Memory usage stable (~150-200 MB total)
- ✅ All validation tests pass

## Support

For issues:
1. Check logs: `make ot-logs`
2. Run validation: `./scripts/validate_phase1.sh`
3. Review troubleshooting section
4. Check individual container logs

## License

Educational/Research Use

---

**Phase 1 v2: Real ICSSIM Stack with Authentic Modbus/TCP Traffic** 🚀
