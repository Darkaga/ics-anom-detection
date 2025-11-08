#!/bin/bash
# =============================================================================
# Phase 2 Validation Script - Collection Layer (Zeek + MinIO)
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

section "Phase 2: Collection Layer Validation"

# Test 1: Docker
if command -v docker &> /dev/null; then
    pass "Docker is installed"
else
    fail "Docker not found"
fi

# Test 2: Check Phase 1 is running
PHASE1_RUNNING=$(docker ps --filter "label=com.ics-anom.phase=1" --filter "status=running" | wc -l)
if [ $PHASE1_RUNNING -ge 4 ]; then
    pass "Phase 1 (OT layer) is running"
else
    warn "Phase 1 not fully running - collection will have limited traffic"
fi

# Test 3: Check MinIO container
if docker ps --format "{{.Names}}" | grep -q "^minio$"; then
    pass "MinIO container running"
else
    fail "MinIO container not running"
fi

# Test 4: Check Zeek container
if docker ps --format "{{.Names}}" | grep -q "^zeek$"; then
    pass "Zeek container running"
else
    fail "Zeek container not running"
fi

# Test 5: MinIO health
if curl -sf http://localhost:9000/minio/health/live > /dev/null 2>&1; then
    pass "MinIO API responding (port 9000)"
else
    fail "MinIO API not responding"
fi

# Test 6: MinIO Console
if curl -sf http://localhost:9001 > /dev/null 2>&1; then
    pass "MinIO Console responding (port 9001)"
else
    warn "MinIO Console not responding (may still be starting)"
fi

# Test 7: Check buckets
section "Storage Buckets"
BUCKETS=$(docker exec minio mc ls minio/ 2>/dev/null | grep -E "(pcaps|zeek-logs|zeek-features|models)" | wc -l)
if [ $BUCKETS -ge 2 ]; then
    pass "Required buckets created ($BUCKETS/4)"
    docker exec minio mc ls minio/ 2>/dev/null | grep -E "(pcaps|zeek-logs|zeek-features|models)" | while read line; do
        echo "  - $line"
    done
else
    warn "Buckets not fully created yet ($BUCKETS/4 found)"
fi

# Test 8: Zeek process
section "Zeek Analysis"
if docker exec zeek pgrep -f zeek > /dev/null 2>&1; then
    pass "Zeek process running"
else
    warn "Zeek process not detected"
fi

# Test 9: Check br_icsnet interface exists for Zeek
if docker exec zeek ip link show br_icsnet > /dev/null 2>&1; then
    pass "Zeek can access br_icsnet interface"
else
    fail "Zeek cannot access br_icsnet interface"
fi

# Test 10: Check for Zeek logs
section "Data Collection"
sleep 5  # Give Zeek a moment to generate logs
ZEEK_LOGS=$(docker exec zeek ls /zeek/logs/*.log 2>/dev/null | wc -l)
if [ $ZEEK_LOGS -gt 0 ]; then
    pass "Zeek generating logs ($ZEEK_LOGS files)"
else
    warn "No Zeek logs detected yet (may be initializing)"
fi

# Summary
section "Summary"
TOTAL=$((PASSED + FAILED))
echo ""
echo -e "Tests passed: ${GREEN}${PASSED}${NC}/${TOTAL}"

if [ $FAILED -gt 0 ]; then
    echo -e "Tests failed: ${RED}${FAILED}${NC}/${TOTAL}"
    echo ""
    echo -e "${RED}Phase 2 validation FAILED${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check logs: make collect-logs"
    echo "  2. Check Zeek: docker logs zeek"
    echo "  3. Check MinIO: docker logs minio"
    echo "  4. Restart: make collect-down && make collect-up"
    exit 1
else
    echo ""
    echo -e "${GREEN}✓ Phase 2 validation PASSED${NC}"
    echo ""
    echo "Collection layer is working!"
    echo ""
    echo "Next steps:"
    echo "  - Access MinIO Console: http://localhost:9001"
    echo "  - Monitor Zeek: make collect-logs-zeek"
    echo "  - Check buckets: docker exec minio mc ls minio/zeek-logs/"
    echo "  - When collecting data (24h): Proceed to Phase 3 (Featurization)"
    exit 0
fi
