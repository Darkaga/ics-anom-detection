#!/bin/bash
# Phase 4 Validation Script - Real-Time Detection & API
# Tests all detection API endpoints and validates functionality

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

API_URL="http://localhost:8000"

echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}Phase 4: Real-Time Detection API Validation${NC}"
echo -e "${BLUE}=================================================${NC}"
echo ""

# Function to check if API is running
check_api() {
    if ! curl -s -f "${API_URL}/health" > /dev/null 2>&1; then
        echo -e "${RED}✗ API not responding at ${API_URL}${NC}"
        echo -e "${YELLOW}Start the API with: make detection-up${NC}"
        exit 1
    fi
}

# Function to pretty print JSON
pretty_json() {
    if command -v jq &> /dev/null; then
        jq '.'
    else
        python3 -m json.tool
    fi
}

echo -e "${BLUE}[1/8] Checking API availability...${NC}"
check_api
echo -e "${GREEN}✓ API is running${NC}"
echo ""

echo -e "${BLUE}[2/8] Testing health endpoint${NC}"
echo "GET ${API_URL}/health"
HEALTH=$(curl -s "${API_URL}/health")
echo "$HEALTH" | pretty_json
echo -e "${GREEN}✓ Health check passed${NC}"
echo ""

echo -e "${BLUE}[3/8] Testing status endpoint${NC}"
echo "GET ${API_URL}/status"
STATUS=$(curl -s "${API_URL}/status")
echo "$STATUS" | pretty_json

DETECTOR_RUNNING=$(echo "$STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin)['detector_running'])")
if [ "$DETECTOR_RUNNING" = "True" ] || [ "$DETECTOR_RUNNING" = "true" ]; then
    echo -e "${GREEN}✓ Detector is running${NC}"
else
    echo -e "${YELLOW}⚠ Detector not running${NC}"
fi
echo ""

echo -e "${BLUE}[4/8] Testing feature info endpoint${NC}"
echo "GET ${API_URL}/info/features"
FEATURES=$(curl -s "${API_URL}/info/features")
NUM_FEATURES=$(echo "$FEATURES" | python3 -c "import sys, json; print(json.load(sys.stdin)['num_features'])")
echo "Number of features: $NUM_FEATURES"
if [ "$NUM_FEATURES" = "28" ]; then
    echo -e "${GREEN}✓ Correct feature count (28)${NC}"
else
    echo -e "${RED}✗ Expected 28 features, got $NUM_FEATURES${NC}"
fi
echo ""

echo -e "${BLUE}[5/8] Testing current anomalies endpoint${NC}"
echo "GET ${API_URL}/anomalies/current?limit=5"
CURRENT=$(curl -s "${API_URL}/anomalies/current?limit=5")
echo "$CURRENT" | pretty_json

ANOMALY_COUNT=$(echo "$CURRENT" | python3 -c "import sys, json; print(json.load(sys.stdin)['count'])")
echo -e "${BLUE}Found $ANOMALY_COUNT recent anomalies${NC}"
echo ""

echo -e "${BLUE}[6/8] Testing statistics endpoint${NC}"
echo "GET ${API_URL}/anomalies/stats"
STATS=$(curl -s "${API_URL}/anomalies/stats")
echo "$STATS" | pretty_json
echo -e "${GREEN}✓ Statistics retrieved${NC}"
echo ""

echo -e "${BLUE}[7/8] Testing historical query endpoint${NC}"
echo "POST ${API_URL}/anomalies/history"
QUERY='{
    "limit": 10
}'
HISTORY=$(curl -s -X POST "${API_URL}/anomalies/history" \
    -H "Content-Type: application/json" \
    -d "$QUERY")
echo "$HISTORY" | pretty_json

HISTORY_COUNT=$(echo "$HISTORY" | python3 -c "import sys, json; print(json.load(sys.stdin)['count'])")
echo -e "${BLUE}Found $HISTORY_COUNT historical anomalies${NC}"
echo ""

echo -e "${BLUE}[8/8] Checking data directories${NC}"

# Check if model exists
if [ -f "../data/models/anomaly_detector.pkl" ]; then
    MODEL_SIZE=$(du -h ../data/models/anomaly_detector.pkl | cut -f1)
    echo -e "${GREEN}✓ Model found: ${MODEL_SIZE}${NC}"
else
    echo -e "${RED}✗ Model not found${NC}"
fi

# Check if log file exists
if [ -f "../data/zeek/modbus_detailed-current.log" ]; then
    LOG_SIZE=$(du -h ../data/zeek/modbus_detailed-current.log | cut -f1)
    LOG_LINES=$(wc -l < ../data/zeek/modbus_detailed-current.log)
    echo -e "${GREEN}✓ Log file found: ${LOG_SIZE} (${LOG_LINES} lines)${NC}"
else
    echo -e "${YELLOW}⚠ Log file not found (may not be created yet)${NC}"
fi

# Check detection output
if [ -d "../data/detections" ]; then
    DETECTION_FILES=$(ls -1 ../data/detections/anomalies_*.parquet 2>/dev/null | wc -l)
    echo -e "${BLUE}Detection output files: ${DETECTION_FILES}${NC}"
    if [ "$DETECTION_FILES" -gt 0 ]; then
        echo -e "${GREEN}✓ Anomalies are being saved${NC}"
    else
        echo -e "${YELLOW}⚠ No detection files yet (may need more time)${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Detection output directory not found${NC}"
fi

echo ""
echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}Validation Summary${NC}"
echo -e "${BLUE}=================================================${NC}"
echo ""

RECORDS_PROCESSED=$(echo "$STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('records_processed', 0))")
ANOMALIES_DETECTED=$(echo "$STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('anomalies_detected', 0))")

echo -e "Records Processed:    ${GREEN}${RECORDS_PROCESSED}${NC}"
echo -e "Anomalies Detected:   ${GREEN}${ANOMALIES_DETECTED}${NC}"
echo -e "API Status:           ${GREEN}Running${NC}"
echo ""

if [ "$RECORDS_PROCESSED" -eq 0 ]; then
    echo -e "${YELLOW}Note: No records processed yet. This is normal if you just started the system.${NC}"
    echo -e "${YELLOW}Wait 5-10 minutes for data to accumulate and check again.${NC}"
    echo ""
fi

echo -e "${GREEN}✓ Phase 4 validation complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Monitor logs:     make detection-logs"
echo "  2. Check status:     make detection-status"
echo "  3. Test endpoints:   make detection-test"
echo "  4. View API docs:    http://localhost:8000/docs"
echo ""
echo "Ready for Phase 5: Dashboard!"
