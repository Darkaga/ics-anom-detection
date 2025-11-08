.PHONY: help init ot-build ot-up ot-down ot-logs ot-test ot-status clean

# =============================================================================
# ICS Anomaly Detection - Makefile (Real ICSSIM Stack)
# =============================================================================

RED=\033[0;31m
GREEN=\033[0;32m
YELLOW=\033[1;33m
BLUE=\033[0;34m
NC=\033[0m

help: ## Show this help message
	@echo "ICS Anomaly Detection - Available Commands"
	@echo "=========================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

init: ## Initialize environment
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(GREEN)✓$(NC) Created .env from template"; \
	else \
		echo "$(YELLOW)!$(NC) .env already exists"; \
	fi

# =============================================================================
# Phase 1: OT Simulator (Real ICSSIM)
# =============================================================================

ot-build: ## Build all ICSSIM containers
	@echo "$(GREEN)Building ICSSIM containers (PLC1, PLC2, HMI1-3, Physical Sim)...$(NC)"
	docker compose -f compose/compose.ot.yaml build
	@echo "$(GREEN)✓$(NC) Build complete"

ot-up: init ## Start full ICSSIM stack
	@echo "$(GREEN)Starting ICSSIM stack...$(NC)"
	docker compose -f compose/compose.ot.yaml up -d
	@echo "$(GREEN)✓$(NC) ICSSIM started"
	@echo ""
	@echo "Containers:"
	@echo "  - PLC1 (192.168.0.11) - Tank controller [Modbus server]"
	@echo "  - PLC2 (192.168.0.12) - Conveyor controller [Modbus server]"
	@echo "  - HMI1 (192.168.0.21) - Operator interface [Modbus client]"
	@echo "  - HMI2 (192.168.0.22) - Operator interface [Modbus client]"
	@echo "  - HMI3 (192.168.0.23) - Operator interface [Modbus client]"
	@echo "  - Physical Sim (192.168.1.31) - Process simulation"
	@echo ""
	@echo "Check status: make ot-status"

ot-up-with-attacker: init ## Start ICSSIM with attacker container
	@echo "$(YELLOW)Starting ICSSIM with attacker...$(NC)"
	docker compose -f compose/compose.ot.yaml --profile attack up -d
	@echo "$(GREEN)✓$(NC) ICSSIM started with attacker (192.168.0.42)"

ot-down: ## Stop ICSSIM stack
	@echo "$(RED)Stopping ICSSIM...$(NC)"
	docker compose -f compose/compose.ot.yaml down

ot-logs: ## Show logs from all ICSSIM containers
	docker compose -f compose/compose.ot.yaml logs -f

ot-logs-plc1: ## Show PLC1 logs
	docker compose -f compose/compose.ot.yaml logs -f plc1

ot-logs-plc2: ## Show PLC2 logs
	docker compose -f compose/compose.ot.yaml logs -f plc2

ot-logs-hmi1: ## Show HMI1 logs
	docker compose -f compose/compose.ot.yaml logs -f hmi1

ot-status: ## Show status of all ICSSIM containers
	@echo "$(BLUE)=== ICSSIM Container Status ===$(NC)"
	@docker ps --filter "label=com.ics-anom.phase=1" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

ot-test: ## Test ICSSIM health
	@echo "$(YELLOW)Testing ICSSIM stack health...$(NC)"
	@RUNNING=$$(docker ps --filter "label=com.ics-anom.phase=1" --filter "status=running" | wc -l); \
	if [ $$RUNNING -ge 6 ]; then \
		echo "$(GREEN)✓$(NC) ICSSIM stack running ($$(($$RUNNING - 1)) containers)"; \
		echo ""; \
		echo "Networks:"; \
		docker network inspect ot_network --format '  {{.Name}}: {{range .Containers}}{{.Name}} {{end}}' 2>/dev/null || true; \
		echo ""; \
		echo "$(YELLOW)Testing Modbus connectivity...$(NC)"; \
		docker exec icssim-hmi1 nc -zv 192.168.0.11 502 2>&1 | grep -q succeeded && echo "$(GREEN)✓$(NC) PLC1 Modbus port accessible" || echo "$(YELLOW)!$(NC) Checking PLC1..."; \
		docker exec icssim-hmi1 nc -zv 192.168.0.12 502 2>&1 | grep -q succeeded && echo "$(GREEN)✓$(NC) PLC2 Modbus port accessible" || echo "$(YELLOW)!$(NC) Checking PLC2..."; \
	else \
		echo "$(RED)✗$(NC) ICSSIM stack not fully running (expected 6+ containers, got $$(($$RUNNING - 1)))"; \
		echo "Start with: make ot-up"; \
		exit 1; \
	fi

ot-shell-plc1: ## Shell into PLC1
	docker compose -f compose/compose.ot.yaml exec plc1 bash

ot-shell-hmi1: ## Shell into HMI1
	docker compose -f compose/compose.ot.yaml exec hmi1 bash

ot-traffic: ## Monitor Modbus traffic on OT network
	@echo "$(YELLOW)Monitoring Modbus traffic on ot_network...$(NC)"
	@echo "Press Ctrl+C to stop"
	@BRIDGE=$$(docker network inspect ot_network -f '{{.Id}}' | cut -c1-12); \
	sudo tcpdump -i br-$$BRIDGE -nn 'tcp port 502' -A

# =============================================================================
# Phase 2: Collection Layer (Zeek + MinIO)
# =============================================================================

collect-build: ## Build collection layer (Zeek + MinIO)
	@echo "$(GREEN)Building Phase 2: Collection Layer...$(NC)"
	docker compose -f compose/compose.collection.yaml build
	@echo "$(GREEN)✓$(NC) Build complete"

collect-up: init ## Start collection layer
	@echo "$(GREEN)Starting Phase 2: Collection Layer...$(NC)"
	docker compose -f compose/compose.collection.yaml up -d
	@echo "$(GREEN)✓$(NC) Collection layer started"
	@echo ""
	@echo "Services:"
	@echo "  - MinIO S3 API: http://localhost:9000"
	@echo "  - MinIO Console: http://localhost:9001"
	@echo "    Login: $$(grep MINIO_ROOT_USER .env | cut -d'=' -f2) / $$(grep MINIO_ROOT_PASSWORD .env | cut -d'=' -f2)"
	@echo "  - Zeek: Capturing from br_icsnet"
	@echo ""
	@echo "Check status: make collect-status"

collect-down: ## Stop collection layer
	@echo "$(RED)Stopping collection layer...$(NC)"
	docker compose -f compose/compose.collection.yaml down

collect-logs: ## Show collection layer logs
	docker compose -f compose/compose.collection.yaml logs -f

collect-logs-zeek: ## Show Zeek logs
	docker compose -f compose/compose.collection.yaml logs -f zeek

collect-logs-minio: ## Show MinIO logs
	docker compose -f compose/compose.collection.yaml logs -f minio

collect-status: ## Show collection layer status
	@echo "$(BLUE)=== Phase 2: Collection Layer Status ===$(NC)"
	@docker ps --filter "label=com.ics-anom.phase=2" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "Not started"

collect-test: ## Test collection layer
	@echo "$(YELLOW)Testing Phase 2: Collection Layer...$(NC)"
	@echo ""
	@echo "1. Checking MinIO..."
	@curl -sf http://localhost:9000/minio/health/live && echo "$(GREEN)✓$(NC) MinIO healthy" || echo "$(RED)✗$(NC) MinIO not responding"
	@echo ""
	@echo "2. Checking buckets..."
	@docker exec minio mc ls minio/ 2>/dev/null | grep -E "(pcaps|zeek-logs)" && echo "$(GREEN)✓$(NC) Buckets created" || echo "$(YELLOW)!$(NC) Buckets not ready"
	@echo ""
	@echo "3. Checking Zeek..."
	@docker exec zeek pgrep -f zeek > /dev/null && echo "$(GREEN)✓$(NC) Zeek process running" || echo "$(RED)✗$(NC) Zeek not running"

# =============================================================================
# Phase 3+4: ML Pipeline (GPU-Accelerated)
# =============================================================================

ml-build: ## Build ML pipeline container
	@echo "$(GREEN)Building ML Pipeline (GPU-accelerated with RAPIDS)...$(NC)"
	@echo "$(YELLOW)Note: This will download ~5GB RAPIDS image - may take 10-15 minutes$(NC)"
	docker compose -f compose/compose.ml.yaml build
	@echo "$(GREEN)✓$(NC) ML pipeline built"

ml-up: ## Start ML pipeline container in background
	@echo "$(GREEN)Starting ML pipeline container...$(NC)"
	docker compose -f compose/compose.ml.yaml up -d
	@echo "$(GREEN)✓$(NC) ML pipeline started"
	@echo ""
	@echo "Usage:"
	@echo "  make ml-shell     - Interactive shell"
	@echo "  make ml-extract   - Extract features"
	@echo "  make ml-train     - Train model"
	@echo "  make ml-down      - Stop container"

ml-shell: ## Start interactive ML shell with GPU
	@echo "$(GREEN)Starting ML pipeline shell...$(NC)"
	docker compose -f compose/compose.ml.yaml run --rm ml-pipeline

ml-extract: ## Extract features from Zeek logs
	@echo "$(GREEN)Extracting features from Zeek logs...$(NC)"
	docker compose -f compose/compose.ml.yaml run --rm ml-pipeline \
		python3 /workspace/scripts/extract_features.py \
		"/workspace/data/zeek/modbus*.log" \
		--output /workspace/data/features \
		--window 300

ml-train: ## Train anomaly detection model
	@echo "$(GREEN)Training anomaly detection model...$(NC)"
	@echo "$(YELLOW)Finding latest feature file...$(NC)"
	docker compose -f compose/compose.ml.yaml run --rm ml-pipeline bash -c '\
		LATEST_FEATURES=$$(ls -t /workspace/data/features/features_*.csv 2>/dev/null | head -1); \
		if [ -z "$$LATEST_FEATURES" ]; then \
			echo "Error: No feature files found. Run make ml-extract first."; \
			exit 1; \
		fi; \
		echo "Using: $$LATEST_FEATURES"; \
		python3 /workspace/scripts/train_model.py \
			$$LATEST_FEATURES \
			--output /workspace/data/models \
			--contamination 0.01'

ml-pipeline: ml-extract ml-train ## Run complete ML pipeline (extract + train)
	@echo "$(GREEN)✓$(NC) ML pipeline complete!"
	@echo ""
	@echo "Results:"
	@echo "  Features: data/features/"
	@echo "  Model: data/models/"
	@echo "  Visualizations: data/models/*.png"

ml-jupyter: ## Start Jupyter notebook server
	@echo "$(GREEN)Starting Jupyter notebook server...$(NC)"
	@echo "Access at: http://localhost:8888"
	docker compose -f compose/compose.ml.yaml run --rm -p 8888:8888 ml-pipeline \
		jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root

ml-down: ## Stop ML pipeline
	docker compose -f compose/compose.ml.yaml down

ml-clean: ## Clean ML artifacts
	@echo "$(YELLOW)Cleaning ML artifacts...$(NC)"
	rm -rf data/features/* data/models/*
	@echo "$(GREEN)✓$(NC) ML artifacts cleaned"

# =============================================================================
# Phase 4: Real-Time Detection & API
# =============================================================================

detection-build: ## Build detection API container
	@echo "$(GREEN)Building detection API container...$(NC)"
	docker compose -f compose/compose.detection.yaml build
	@echo "$(GREEN)✓$(NC) Build complete"

detection-up: ## Start real-time detection API
	@echo "$(GREEN)Starting real-time detection API...$(NC)"
	@if [ ! -f data/models/anomaly_detector.pkl ]; then \
		echo "$(RED)Error: Trained model not found!$(NC)"; \
		echo "Run 'make ml-pipeline' first to train the model."; \
		exit 1; \
	fi
	docker compose -f compose/compose.detection.yaml up -d
	@echo "$(GREEN)✓$(NC) Detection API started"
	@echo ""
	@echo "API Endpoints:"
	@echo "  - Health:        http://localhost:8000/health"
	@echo "  - Status:        http://localhost:8000/status"
	@echo "  - Current:       http://localhost:8000/anomalies/current"
	@echo "  - History:       http://localhost:8000/anomalies/history (POST)"
	@echo "  - Stats:         http://localhost:8000/anomalies/stats"
	@echo "  - Features:      http://localhost:8000/info/features"
	@echo "  - API Docs:      http://localhost:8000/docs"
	@echo ""
	@echo "Monitor logs: make detection-logs"

detection-down: ## Stop detection API
	docker compose -f compose/compose.detection.yaml down

detection-logs: ## Show detection API logs
	docker compose -f compose/compose.detection.yaml logs -f

detection-restart: detection-down detection-up ## Restart detection API

detection-status: ## Check detection API status
	@echo "$(BLUE)Checking detection API status...$(NC)"
	@curl -s http://localhost:8000/status | python3 -m json.tool || echo "API not responding"

detection-test: ## Test detection API endpoints
	@echo "$(BLUE)Testing detection API endpoints...$(NC)"
	@echo ""
	@echo "$(GREEN)1. Health Check:$(NC)"
	@curl -s http://localhost:8000/health | python3 -m json.tool
	@echo ""
	@echo "$(GREEN)2. Status:$(NC)"
	@curl -s http://localhost:8000/status | python3 -m json.tool
	@echo ""
	@echo "$(GREEN)3. Recent Anomalies:$(NC)"
	@curl -s http://localhost:8000/anomalies/current | python3 -m json.tool
	@echo ""
	@echo "$(GREEN)4. Statistics:$(NC)"
	@curl -s http://localhost:8000/anomalies/stats | python3 -m json.tool

detection-clean: ## Clean detection output files
	@echo "$(YELLOW)Cleaning detection output...$(NC)"
	rm -rf data/detections/*
	@echo "$(GREEN)✓$(NC) Detection output cleaned"

# =============================================================================
# Phase 5 & 6: Dashboard + Attacker
# =============================================================================

dashboard-build: ## Build dashboard and attacker containers
	@echo "$(GREEN)Building dashboard and attacker...$(NC)"
	docker compose -f compose/compose.dashboard.yaml build
	@echo "$(GREEN)✓$(NC) Build complete"

dashboard-up: ## Start dashboard and attacker
	@echo "$(GREEN)Starting dashboard and attacker...$(NC)"
	docker compose -f compose/compose.dashboard.yaml up -d
	@echo "$(GREEN)✓$(NC) Dashboard started"
	@echo ""
	@echo "Access dashboard at: http://localhost:8501"
	@echo "Attack API at: http://localhost:8002"
	@echo "Detection API at: http://localhost:8001"

dashboard-down: ## Stop dashboard and attacker
	@echo "$(RED)Stopping dashboard and attacker...$(NC)"
	docker compose -f compose/compose.dashboard.yaml down

dashboard-logs: ## Show dashboard logs
	docker compose -f compose/compose.dashboard.yaml logs -f

dashboard-logs-dash: ## Show dashboard logs only
	docker logs ics-dashboard -f

dashboard-logs-attack: ## Show attacker logs only
	docker logs ics-attacker -f

dashboard-restart: ## Restart dashboard
	@echo "$(YELLOW)Restarting dashboard...$(NC)"
	docker compose -f compose/compose.dashboard.yaml restart ics-dashboard
	@echo "$(GREEN)✓$(NC) Dashboard restarted"

dashboard-status: ## Check dashboard status
	@echo "$(BLUE)=== Dashboard Status ===$(NC)"
	@docker ps --filter "name=ics-dashboard" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
	@echo ""
	@echo "$(BLUE)=== Attacker Status ===$(NC)"
	@docker ps --filter "name=ics-attacker" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# =============================================================================
# Utility Commands
# =============================================================================

status: ## Show status of all services
	@echo "$(BLUE)=== Phase 1: ICSSIM Stack ===$(NC)"
	@docker compose -f compose/compose.ot.yaml ps 2>/dev/null || echo "Not started"
	@echo ""
	@echo "$(BLUE)=== Phase 2: Collection Stack ===$(NC)"
	@docker compose -f compose/compose.collection.yaml ps 2>/dev/null || echo "Not started"
	@echo ""
	@echo "$(BLUE)=== Phase 4: Detection API ===$(NC)"
	@docker compose -f compose/compose.detection.yaml ps 2>/dev/null || echo "Not started"
	@echo ""
	@echo "$(BLUE)=== Phase 5 & 6: Dashboard + Attacker ===$(NC)"
	@docker compose -f compose/compose.dashboard.yaml ps 2>/dev/null || echo "Not started"
	@echo ""
	@echo "$(BLUE)=== Networks ===$(NC)"
	@docker network ls --filter "label=com.ics-anom.network" 2>/dev/null || echo "None"

clean: ## Stop all services and remove volumes
	@echo "$(RED)Stopping all services...$(NC)"
	docker compose -f compose/compose.ot.yaml down -v 2>/dev/null || true
	@echo "$(GREEN)✓$(NC) Cleanup complete"

clean-all: clean ## Full cleanup including images
	@echo "$(RED)Removing all images...$(NC)"
	docker compose -f compose/compose.ot.yaml down -v --rmi all 2>/dev/null || true
	@echo "$(GREEN)✓$(NC) Full cleanup complete"

logs: ## Show all logs
	docker compose -f compose/compose.ot.yaml logs -f 2>/dev/null || echo "No services running"