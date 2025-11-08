#!/bin/bash
# =============================================================================
# ICSSIM Real Stack - Initial Setup Script
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}ICS Anomaly Detection - Setup (Real ICSSIM)${NC}"
echo -e "${BLUE}=================================================${NC}"
echo ""

# Check Docker
echo -e "${YELLOW}Checking Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not found${NC}"
    exit 1
fi
DOCKER_VERSION=$(docker --version)
echo -e "${GREEN}✓ Docker found: ${DOCKER_VERSION}${NC}"

# Check Docker Compose
echo -e "${YELLOW}Checking Docker Compose...${NC}"
if ! docker compose version &> /dev/null; then
    echo -e "${RED}✗ Docker Compose not found${NC}"
    exit 1
fi
COMPOSE_VERSION=$(docker compose version)
echo -e "${GREEN}✓ Docker Compose found: ${COMPOSE_VERSION}${NC}"

# Check GPU (optional)
echo -e "${YELLOW}Checking NVIDIA GPU...${NC}"
if command -v nvidia-smi &> /dev/null; then
    GPU_INFO=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)
    echo -e "${GREEN}✓ GPU found: ${GPU_INFO}${NC}"
    
    if docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
        echo -e "${GREEN}✓ NVIDIA Docker runtime working${NC}"
    else
        echo -e "${YELLOW}! GPU found but Docker runtime not configured${NC}"
    fi
else
    echo -e "${YELLOW}! No GPU found (optional for Phase 4)${NC}"
fi

# Create .env
echo ""
echo -e "${YELLOW}Checking environment configuration...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env from template${NC}"
else
    echo -e "${GREEN}✓ .env already exists${NC}"
fi

# Check network interfaces
echo ""
echo -e "${YELLOW}Checking network interfaces...${NC}"
if ip addr show ens18 &> /dev/null; then
    ENS18_IP=$(ip -4 addr show ens18 | grep inet | awk '{print $2}' | cut -d/ -f1)
    echo -e "${GREEN}✓ ens18 found: ${ENS18_IP}${NC}"
else
    echo -e "${YELLOW}! ens18 not found${NC}"
fi

if ip addr show ens19 &> /dev/null; then
    echo -e "${GREEN}✓ ens19 found (OT capture interface)${NC}"
else
    echo -e "${YELLOW}! ens19 not found${NC}"
fi

# Check for conflicting networks
echo ""
echo -e "${YELLOW}Checking for network conflicts...${NC}"
if docker network inspect ot_network &>/dev/null; then
    echo -e "${YELLOW}! ot_network already exists (may be from previous deployment)${NC}"
    echo -e "${YELLOW}  Run 'docker network rm ot_network' if you want to recreate it${NC}"
fi

if docker network inspect ot_net &>/dev/null; then
    echo -e "${YELLOW}! ot_net exists (from Phase 1 v1)${NC}"
    echo -e "${YELLOW}  You may want to stop v1 first: cd ~/ics-anom-demo && make ot-down${NC}"
fi

# Check disk space
echo ""
echo -e "${YELLOW}Checking disk space...${NC}"
AVAILABLE=$(df -h . | awk 'NR==2 {print $4}')
echo -e "${GREEN}✓ Available space: ${AVAILABLE}${NC}"

# Create directories
echo ""
echo -e "${YELLOW}Creating data directories...${NC}"
mkdir -p data/pcaps data/zeek data/storage notebooks
echo -e "${GREEN}✓ Directories created${NC}"

# Summary
echo ""
echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}Setup Complete!${NC}"
echo -e "${BLUE}=================================================${NC}"
echo ""
echo -e "Next steps:"
echo -e "  1. Review ${YELLOW}.env${NC} if needed (defaults should work)"
echo -e "  2. ${GREEN}make ot-build${NC} to build all containers (~10-15 min)"
echo -e "  3. ${GREEN}make ot-up${NC} to start the ICSSIM stack"
echo -e "  4. ${GREEN}./scripts/validate_phase1.sh${NC} to verify"
echo -e "  5. ${GREEN}make ot-traffic${NC} to see real Modbus packets!"
echo ""
echo -e "Documentation:"
echo -e "  - ${BLUE}README.md${NC} - Overview"
echo -e "  - ${BLUE}docs/phase1-v2.md${NC} - Detailed guide"
echo -e "  - ${BLUE}TRANSITION_FROM_V1.md${NC} - Migration notes"
echo ""
