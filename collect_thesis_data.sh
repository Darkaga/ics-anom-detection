#!/bin/bash
# Comprehensive Attack Data Collection for Thesis

echo "=========================================="
echo "ML-Based ICS Anomaly Detection"
echo "Comprehensive Attack Evaluation"
echo "=========================================="
echo ""

# Create results directory
RESULTS_DIR="thesis_results_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

echo "Results will be saved to: $RESULTS_DIR"
echo ""

# Function to run attack and collect data
run_attack_test() {
    ATTACK_TYPE=$1
    ATTACK_NAME=$2
    TARGET=$3
    DURATION=$4
    
    echo "=========================================="
    echo "Testing: $ATTACK_NAME"
    echo "=========================================="
    
    # Clear previous detection logs
    docker compose -f compose/compose.detection.yaml restart
    sleep 10
    
    # Baseline - collect normal traffic stats
    echo "Collecting baseline (30s)..."
    sleep 30
    BASELINE_ANOMALIES=$(docker logs ics-detection-api 2>&1 | grep "ANOMALY DETECTED" | wc -l)
    echo "   Baseline anomalies: $BASELINE_ANOMALIES"
    
    # Launch attack
    echo "Launching $ATTACK_NAME attack..."
    ATTACK_RESPONSE=$(curl -s -X POST http://localhost:8002/attacks/execute \
      -H "Content-Type: application/json" \
      -d "{\"attack_type\": \"$ATTACK_TYPE\", \"target\": \"$TARGET\", \"duration\": $DURATION}")
    
    ATTACK_ID=$(echo "$ATTACK_RESPONSE" | jq -r '.attack_id')
    echo "   Attack ID: $ATTACK_ID"
    echo "$ATTACK_RESPONSE" > "$RESULTS_DIR/${ATTACK_NAME}_launch.json"
    
    # Monitor attack progress
    echo "Monitoring attack ($DURATION seconds + analysis time)..."
    for i in {1..18}; do  # 18 * 20s = 6 minutes
        sleep 20
        CURRENT=$(docker logs ics-detection-api 2>&1 | grep "ANOMALY DETECTED" | wc -l)
        DELTA=$((CURRENT - BASELINE_ANOMALIES))
        echo "   [$((i*20))s] New anomalies: $DELTA"
    done
    
    # Collect results
    echo "Collecting detection results..."
    
    # Get all anomalies detected during attack
    docker logs ics-detection-api 2>&1 | grep "ANOMALY DETECTED" > "$RESULTS_DIR/${ATTACK_NAME}_detections.log"
    
    # Get API stats
    curl -s http://localhost:8001/anomalies/stats | jq '.' > "$RESULTS_DIR/${ATTACK_NAME}_stats.json"
    
    # Get recent anomalies with details
    curl -s http://localhost:8001/anomalies/current?limit=50 | jq '.' > "$RESULTS_DIR/${ATTACK_NAME}_current.json"
    
    # Get attack status
    curl -s http://localhost:8002/attacks/status/$ATTACK_ID | jq '.' > "$RESULTS_DIR/${ATTACK_NAME}_attack_status.json"
    
    # Calculate metrics
    TOTAL_DETECTED=$(($(docker logs ics-detection-api 2>&1 | grep "ANOMALY DETECTED" | wc -l) - BASELINE_ANOMALIES))
    
    echo ""
    echo "   Results for $ATTACK_NAME:"
    echo "   Total anomalies detected: $TOTAL_DETECTED"
    echo "   Detection rate: $([ $TOTAL_DETECTED -gt 0 ] && echo 'DETECTED ✓' || echo 'NOT DETECTED ✗')"
    echo ""
    
    # Save summary
    cat > "$RESULTS_DIR/${ATTACK_NAME}_summary.txt" << EOF
Attack Type: $ATTACK_NAME
Attack ID: $ATTACK_ID
Target: $TARGET
Duration: ${DURATION}s
Baseline Anomalies: $BASELINE_ANOMALIES
Total Detected: $TOTAL_DETECTED
Detection: $([ $TOTAL_DETECTED -gt 0 ] && echo 'SUCCESS' || echo 'FAILED')
Timestamp: $(date)
EOF
    
    echo "Results saved to $RESULTS_DIR/"
    echo ""
    
    # Wait for system to stabilize before next test
    echo "Cooling down (60s)..."
    sleep 60
}

# Test all attack types
echo "Starting comprehensive attack evaluation..."
echo "This will take approximately 30-40 minutes."
echo ""

# 1. DoS Flood (already tested, but let's get fresh data)
run_attack_test "dos_flood" "DoS_Flood" "plc1" 60

# 2. Response Injection
run_attack_test "response_injection" "Response_Injection" "plc1" 60

# 3. Reconnaissance
run_attack_test "reconnaissance" "Reconnaissance" "plc1" 60

# Create comprehensive summary
echo "=========================================="
echo "Creating Comprehensive Summary"
echo "=========================================="

cat > "$RESULTS_DIR/THESIS_SUMMARY.txt" << EOF
===================================================================
ML-Based Anomaly Detection in ICS/OT Networks
Comprehensive Attack Evaluation Results
===================================================================

Test Date: $(date)
System Configuration:
- Model: Isolation Forest (28 features)
- Threshold: -0.70
- Window Size: 300 seconds
- Analysis Frequency: Every 5 seconds

-------------------------------------------------------------------
DETECTION RESULTS BY ATTACK TYPE
-------------------------------------------------------------------

EOF

# Add results for each attack
for attack in DoS_Flood Response_Injection Reconnaissance; do
    if [ -f "$RESULTS_DIR/${attack}_summary.txt" ]; then
        cat "$RESULTS_DIR/${attack}_summary.txt" >> "$RESULTS_DIR/THESIS_SUMMARY.txt"
        echo "" >> "$RESULTS_DIR/THESIS_SUMMARY.txt"
        echo "-------------------------------------------------------------------" >> "$RESULTS_DIR/THESIS_SUMMARY.txt"
        echo "" >> "$RESULTS_DIR/THESIS_SUMMARY.txt"
    fi
done

# Copy latest detection files
echo "Copying detection data files..."
docker cp ics-detection-api:/data/detections/. "$RESULTS_DIR/detection_files/" 2>/dev/null || echo "No detection files to copy"

# Export system logs
echo "Exporting system logs..."
docker logs ics-detection-api > "$RESULTS_DIR/detector_full_log.txt" 2>&1
docker logs zeek > "$RESULTS_DIR/zeek_log.txt" 2>&1

# Create data collection summary
cat > "$RESULTS_DIR/DATA_INVENTORY.txt" << EOF
===================================================================
DATA COLLECTION INVENTORY FOR THESIS
===================================================================

Collection Date: $(date)
Results Directory: $RESULTS_DIR

-------------------------------------------------------------------
DETECTION RESULTS
-------------------------------------------------------------------
- *_detections.log: Raw detection logs per attack
- *_stats.json: Statistical summary per attack
- *_current.json: Detailed anomaly records
- *_attack_status.json: Attack execution status
- *_summary.txt: Per-attack summary

-------------------------------------------------------------------
SYSTEM LOGS
-------------------------------------------------------------------
- detector_full_log.txt: Complete detection engine logs
- zeek_log.txt: Network capture logs

-------------------------------------------------------------------
DETECTION DATA FILES (Parquet)
-------------------------------------------------------------------
Directory: detection_files/
Format: Parquet (columnar, efficient)
Contents: Timestamped anomaly records with feature values

-------------------------------------------------------------------
THESIS METRICS TO EXTRACT
-------------------------------------------------------------------
For each attack type, calculate:
1. True Positives (TP): Anomalies during attack
2. False Positives (FP): Anomalies during baseline
3. Detection Rate: TP / Total attack windows
4. Precision: TP / (TP + FP)
5. Average anomaly score during attack
6. Detection latency (time from attack start to first detection)

-------------------------------------------------------------------
RECOMMENDED ANALYSIS
-------------------------------------------------------------------
1. Load detection_files/*.parquet into pandas
2. Analyze feature values during each attack type
3. Identify which features were most discriminative
4. Compare anomaly scores across attack types
5. Generate confusion matrices per attack
6. Create time-series plots of detection timeline

EOF

echo ""
echo "=========================================="
echo "DATA COLLECTION COMPLETE!"
echo "=========================================="
echo ""
echo "Results directory: $RESULTS_DIR"
echo ""
