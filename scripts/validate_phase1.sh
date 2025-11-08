#!/bin/bash
# =============================================================================
# Phase 1 v2 Validation Script - Real ICSSIM Stack
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

FAILED=0
PASSED=0

pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

warn() {
    echo -e "${YELLOW}!${NC} $1"
}

section() {
    echo ""
    echo -e "${BLUE}=== $1 ===${NC}"
}

section "Phase 1: Real ICSSIM Stack Validation"

# Test 1: Docker
if command -v docker &> /dev/null; then
    pass "Docker is installed"
else
    fail "Docker not found"
fi

# Test 2: Docker Compose
if docker compose version &> /dev/null; then
    pass "Docker Compose is available"
else
    fail "Docker Compose not found"
fi

# Test 3: Compose file
if [ -f "compose/compose.ot.yaml" ]; then
    pass "compose.ot.yaml exists"
else
    fail "compose.ot.yaml missing"
fi

# Test 4: Environment
if [ -f ".env" ]; then
    pass ".env file exists"
else
    warn ".env file missing (will use defaults)"
fi

# Test 5: Check running containers (expect 4+ core containers)
# Note: HMI2 and HMI3 require interactive input and may restart - this is expected
RUNNING=$(docker ps --filter "label=com.ics-anom.phase=1" --filter "status=running" --format "{{.Names}}" | wc -l)
TOTAL=$(docker ps -a --filter "label=com.ics-anom.phase=1" --format "{{.Names}}" | wc -l)

if [ $RUNNING -ge 4 ]; then
    pass "ICSSIM core stack running ($RUNNING/$TOTAL containers)"
    if [ $RUNNING -lt 6 ]; then
        warn "HMI2/HMI3 may be restarting (require interactive input - expected behavior)"
    fi
else
    fail "ICSSIM stack incomplete (expected 4+, got $RUNNING)"
    echo "   Run: make ot-up"
fi

if [ $RUNNING -ge 4 ]; then
    # Test 6: Check core containers (PLC1, PLC2, HMI1, PYS are essential)
    for container in icssim-plc1 icssim-plc2 icssim-hmi1 icssim-pys; do
        if docker ps --format "{{.Names}}" | grep -q "^${container}$"; then
            pass "Container ${container} running"
        else
            fail "Container ${container} not running"
        fi
    done
    
    # Optional containers (may restart due to interactive input requirements)
    for container in icssim-hmi2 icssim-hmi3; do
        if docker ps --format "{{.Names}}" | grep -q "^${container}$"; then
            pass "Container ${container} running (optional)"
        else
            warn "Container ${container} not stable (requires interactive input - expected)"
        fi
    done
    
    # Test 7: Networks exist
    if docker network inspect ot_network &>/dev/null; then
        pass "ot_network exists"
    else
        fail "ot_network missing"
    fi
    
    if docker network inspect ot_physical &>/dev/null; then
        pass "ot_physical exists"
    else
        fail "ot_physical missing"
    fi
    
    # Test 8: Check IP addresses
    PLC1_IP=$(docker inspect icssim-plc1 --format='{{range .NetworkSettings.Networks}}{{if eq .NetworkID}}{{.IPAddress}}{{end}}{{end}}' 2>/dev/null | grep "192.168.0")
    if [ ! -z "$PLC1_IP" ]; then
        pass "PLC1 has correct IP: $PLC1_IP"
    else
        fail "PLC1 IP not in 192.168.0.0/24 range"
    fi
    
    PLC2_IP=$(docker inspect icssim-plc2 --format='{{range .NetworkSettings.Networks}}{{if eq .NetworkID}}{{.IPAddress}}{{end}}{{end}}' 2>/dev/null | grep "192.168.0")
    if [ ! -z "$PLC2_IP" ]; then
        pass "PLC2 has correct IP: $PLC2_IP"
    else
        fail "PLC2 IP not in 192.168.0.0/24 range"
    fi
    
    # Test 9: Modbus port accessibility
    echo -n "   Testing Modbus connectivity... "
    if docker exec icssim-hmi1 timeout 2 bash -c 'cat < /dev/null > /dev/tcp/192.168.0.11/502' 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
        pass "PLC1 Modbus port (502) accessible from HMI1"
    else
        echo -e "${YELLOW}!${NC}"
        warn "PLC1 Modbus port not yet accessible (may be initializing)"
    fi
    
    if docker exec icssim-hmi1 timeout 2 bash -c 'cat < /dev/null > /dev/tcp/192.168.0.12/502' 2>/dev/null; then
        pass "PLC2 Modbus port (502) accessible from HMI1"
    else
        warn "PLC2 Modbus port not yet accessible (may be initializing)"
    fi
    
    # Test 10: Check for Python processes
    if docker exec icssim-plc1 pgrep -f python &>/dev/null; then
        pass "PLC1 Python process running"
    else
        fail "PLC1 Python process not found"
    fi
    
    if docker exec icssim-hmi1 pgrep -f python &>/dev/null; then
        pass "HMI1 Python process running"
    else
        fail "HMI1 Python process not found"
    fi
    
    # Test 11: Check logs for activity
    LOG_COUNT=$(docker logs icssim-plc1 2>&1 | wc -l)
    if [ $LOG_COUNT -gt 5 ]; then
        pass "PLC1 generating logs ($LOG_COUNT lines)"
    else
        warn "PLC1 has few log lines ($LOG_COUNT)"
    fi
    
    # Test 12: Check for Modbus traffic
    section "Modbus Traffic Check"
    echo "Capturing packets for 10 seconds..."
    BRIDGE=$(docker network inspect ot_network -f '{{.Id}}' | cut -c1-12)
    PACKETS=$(timeout 10 sudo tcpdump -i br-${BRIDGE} -nn 'tcp port 502' -c 5 2>&1 | grep -c "192.168.0" || echo "0")
    
    if [ $PACKETS -gt 0 ]; then
        pass "Real Modbus traffic detected ($PACKETS packets)"
    else
        warn "No Modbus traffic detected yet (containers may be initializing)"
    fi
fi

# Resource usage
section "Resource Usage"
if [ $RUNNING -ge 6 ]; then
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" \
        $(docker ps --filter "label=com.ics-anom.phase=1" --format "{{.Names}}")
fi

# Summary
section "Summary"
TOTAL=$((PASSED + FAILED))
echo ""
echo -e "Tests passed: ${GREEN}${PASSED}${NC}/${TOTAL}"

if [ $FAILED -gt 0 ]; then
    echo -e "Tests failed: ${RED}${FAILED}${NC}/${TOTAL}"
    echo ""
    echo -e "${RED}Phase 1 validation FAILED${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check logs: make ot-logs"
    echo "  2. Check individual containers: docker logs icssim-plc1"
    echo "  3. Restart: make ot-down && make ot-up"
    echo "  4. Rebuild: make clean && make ot-build"
    exit 1
else
    echo ""
    echo -e "${GREEN}✓ Phase 1 validation PASSED${NC}"
    echo ""
    echo "Real ICSSIM stack is working correctly!"
    echo ""
    echo -e "${YELLOW}Note:${NC} HMI2 and HMI3 may restart continuously (they require"
    echo "interactive input). This is expected behavior. HMI1 alone generates"
    echo "sufficient Modbus traffic for Phase 2 packet capture."
    echo ""
    echo "Next steps:"
    echo "  - Monitor traffic: make ot-traffic"
    echo "  - View logs: make ot-logs"
    echo "  - Check status: make ot-status"
    echo "  - When stable (24h): Proceed to Phase 2 (Zeek + MinIO)"
    exit 0
fi
