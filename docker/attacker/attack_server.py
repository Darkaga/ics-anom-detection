#!/usr/bin/env python3
"""
Attack Server API
Provides REST endpoints to execute attack scenarios against ICS targets
"""

import asyncio
import logging
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ICS Attack Server",
    description="Execute attack scenarios against ICS targets",
    version="1.0.0"
)

# Enable CORS for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Track running attacks
running_attacks: Dict[str, Dict] = {}

# Available targets (PLCs)
TARGETS = {
    "plc1": "192.168.0.11",
    "plc2": "192.168.0.12"
}

# Available attack types
ATTACKS = {
    "recon_scan": {
        "name": "Reconnaissance Scan",
        "description": "Rapidly enumerate all registers to map PLC memory",
        "script": "attacks/recon_scan.py",
        "expected_detection": "High read frequency anomaly"
    },
    "unauthorized_write": {
        "name": "Unauthorized Writes",
        "description": "Write random values to control registers",
        "script": "attacks/unauthorized_write.py",
        "expected_detection": "Unusual write patterns"
    },
    "command_injection": {
        "name": "Command Injection",
        "description": "Send malformed and unusual Modbus operations",
        "script": "attacks/command_injection.py",
        "expected_detection": "Protocol anomalies"
    },
    "dos_flood": {
        "name": "Denial of Service",
        "description": "Flood PLC with rapid requests",
        "script": "attacks/dos_flood.py",
        "expected_detection": "Extreme timing anomalies"
    }
}


class AttackRequest(BaseModel):
    """Request to execute an attack"""
    attack_type: str = Field(..., description="Type of attack (recon_scan, unauthorized_write, etc.)")
    target: str = Field(..., description="Target PLC (plc1, plc2)")
    duration: int = Field(30, ge=5, le=300, description="Attack duration in seconds")


class AttackResponse(BaseModel):
    """Response after launching attack"""
    attack_id: str
    status: str
    message: str
    attack_type: str
    target: str
    started_at: str


class AttackStatus(BaseModel):
    """Status of a running or completed attack"""
    attack_id: str
    attack_type: str
    target: str
    status: str
    started_at: str
    completed_at: Optional[str]
    duration: Optional[float]
    result: Optional[Dict]


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "ICS Attack Server",
        "version": "1.0.0",
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    """Health check"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/attacks/available")
async def list_attacks():
    """List available attack types"""
    return {
        "attacks": ATTACKS,
        "targets": TARGETS
    }


@app.post("/attacks/execute", response_model=AttackResponse)
async def execute_attack(request: AttackRequest):
    """Execute an attack scenario"""
    
    # Validate attack type
    if request.attack_type not in ATTACKS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown attack type: {request.attack_type}. Available: {list(ATTACKS.keys())}"
        )
    
    # Validate target
    if request.target not in TARGETS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown target: {request.target}. Available: {list(TARGETS.keys())}"
        )
    
    # Generate attack ID
    attack_id = f"{request.attack_type}_{request.target}_{int(time.time())}"
    
    # Get target IP
    target_ip = TARGETS[request.target]
    
    # Get attack script
    script = ATTACKS[request.attack_type]["script"]
    
    # Create attack record
    attack_record = {
        "attack_id": attack_id,
        "attack_type": request.attack_type,
        "target": request.target,
        "target_ip": target_ip,
        "duration": request.duration,
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "result": None
    }
    
    running_attacks[attack_id] = attack_record
    
    # Launch attack in background
    asyncio.create_task(run_attack_background(attack_id, script, target_ip, request.duration))
    
    logger.info(f"Launched attack: {attack_id} ({request.attack_type} on {request.target})")
    
    return AttackResponse(
        attack_id=attack_id,
        status="running",
        message=f"Attack launched successfully. Monitor with /attacks/status/{attack_id}",
        attack_type=request.attack_type,
        target=request.target,
        started_at=attack_record["started_at"]
    )


async def run_attack_background(attack_id: str, script: str, target_ip: str, duration: int):
    """Run attack script in background"""
    try:
        logger.info(f"Running attack {attack_id}: {script} {target_ip} {duration}")
        
        # Execute attack script
        process = await asyncio.create_subprocess_exec(
            "python3", script, target_ip, str(duration),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        # Parse output (look for the result dict in stdout)
        result = {
            "return_code": process.returncode,
            "output": stdout.decode() if stdout else "",
            "error": stderr.decode() if stderr else ""
        }
        
        # Update attack record
        running_attacks[attack_id]["status"] = "completed" if process.returncode == 0 else "failed"
        running_attacks[attack_id]["completed_at"] = datetime.now().isoformat()
        running_attacks[attack_id]["result"] = result
        
        logger.info(f"Attack {attack_id} completed with status: {running_attacks[attack_id]['status']}")
        
    except Exception as e:
        logger.error(f"Error running attack {attack_id}: {e}", exc_info=True)
        running_attacks[attack_id]["status"] = "error"
        running_attacks[attack_id]["completed_at"] = datetime.now().isoformat()
        running_attacks[attack_id]["result"] = {"error": str(e)}


@app.get("/attacks/status/{attack_id}", response_model=AttackStatus)
async def get_attack_status(attack_id: str):
    """Get status of an attack"""
    if attack_id not in running_attacks:
        raise HTTPException(status_code=404, detail=f"Attack not found: {attack_id}")
    
    attack = running_attacks[attack_id]
    
    # Calculate duration if completed
    duration = None
    if attack["completed_at"]:
        started = datetime.fromisoformat(attack["started_at"])
        completed = datetime.fromisoformat(attack["completed_at"])
        duration = (completed - started).total_seconds()
    
    return AttackStatus(
        attack_id=attack_id,
        attack_type=attack["attack_type"],
        target=attack["target"],
        status=attack["status"],
        started_at=attack["started_at"],
        completed_at=attack["completed_at"],
        duration=duration,
        result=attack["result"]
    )


@app.get("/attacks/running")
async def list_running_attacks():
    """List all running attacks"""
    running = [
        attack for attack in running_attacks.values()
        if attack["status"] == "running"
    ]
    return {"count": len(running), "attacks": running}


@app.get("/attacks/history")
async def get_attack_history():
    """Get history of all attacks"""
    return {
        "count": len(running_attacks),
        "attacks": list(running_attacks.values())
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info")
