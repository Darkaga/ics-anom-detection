#!/usr/bin/env python3
"""
FastAPI REST API for ICS Anomaly Detection
Provides endpoints for monitoring, querying, and managing detection
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import pyarrow.parquet as pq
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from detector import RealtimeDetector

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global detector instance
detector: Optional[RealtimeDetector] = None
detector_task: Optional[asyncio.Task] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global detector, detector_task
    
    # Startup
    logger.info("Starting ICS Anomaly Detection API")
    
    # Initialize detector
    log_file = os.getenv('LOG_FILE', '/data/zeek/modbus_detailed-current.log')
    model_path = os.getenv('MODEL_PATH', '/data/models/anomaly_detector.pkl')
    output_dir = os.getenv('OUTPUT_DIR', '/data/detections')
    window_seconds = int(os.getenv('WINDOW_SECONDS', '300'))
    poll_interval = int(os.getenv('POLL_INTERVAL', '5'))
    anomaly_threshold = float(os.getenv('ANOMALY_THRESHOLD', '-0.5'))
    
    detector = RealtimeDetector(
        log_file=log_file,
        model_path=model_path,
        output_dir=output_dir,
        window_seconds=window_seconds,
        poll_interval=poll_interval,
        anomaly_threshold=anomaly_threshold
    )
    
    # Start detection loop in background
    detector_task = asyncio.create_task(detector.start())
    logger.info("Detection engine started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down detection engine")
    if detector:
        await detector.stop()
    if detector_task:
        detector_task.cancel()
        try:
            await detector_task
        except asyncio.CancelledError:
            pass
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="ICS Anomaly Detection API",
    description="Real-time anomaly detection for Industrial Control Systems",
    version="1.0.0",
    lifespan=lifespan
)


# =============================================================================
# Pydantic Models
# =============================================================================

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    version: str = "1.0.0"


class StatusResponse(BaseModel):
    """System status response"""
    status: str
    detector_running: bool
    started_at: str
    records_processed: int
    anomalies_detected: int
    last_check: Optional[str]
    current_window: Optional[int]


class Anomaly(BaseModel):
    """Anomaly detection result"""
    time_window: int
    src: str
    dst: str
    anomaly_score: float
    detected_at: str
    value_mean_mean: Optional[float] = None
    read_count_sum: Optional[int] = None
    registers_accessed: Optional[int] = None


class AnomaliesResponse(BaseModel):
    """Response containing list of anomalies"""
    count: int
    anomalies: List[Dict]


class HistoricalQuery(BaseModel):
    """Query parameters for historical anomalies"""
    start_time: Optional[str] = Field(None, description="ISO format timestamp")
    end_time: Optional[str] = Field(None, description="ISO format timestamp")
    src: Optional[str] = Field(None, description="Source IP filter")
    dst: Optional[str] = Field(None, description="Destination IP filter")
    min_score: Optional[float] = Field(None, description="Minimum anomaly score")
    limit: int = Field(100, description="Maximum results to return")


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/", response_class=JSONResponse)
async def root():
    """Root endpoint"""
    return {
        "service": "ICS Anomaly Detection API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "status": "/status",
            "current": "/anomalies/current",
            "history": "/anomalies/history",
            "stats": "/anomalies/stats"
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat()
    )


@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Get detection system status"""
    if detector is None:
        raise HTTPException(status_code=503, detail="Detector not initialized")
    
    status = detector.get_status()
    
    return StatusResponse(
        status="running" if detector.running else "stopped",
        detector_running=detector.running,
        started_at=status['started_at'],
        records_processed=status['records_processed'],
        anomalies_detected=status['anomalies_detected'],
        last_check=status['last_check'],
        current_window=status['current_window']
    )


@app.get("/anomalies/current", response_model=AnomaliesResponse)
async def get_current_anomalies(
    limit: int = Query(20, ge=1, le=100, description="Number of recent anomalies")
):
    """Get most recent anomalies from memory"""
    if detector is None:
        raise HTTPException(status_code=503, detail="Detector not initialized")
    
    anomalies = detector.get_recent_anomalies(limit=limit)
    
    return AnomaliesResponse(
        count=len(anomalies),
        anomalies=anomalies
    )


@app.post("/anomalies/history", response_model=AnomaliesResponse)
async def query_historical_anomalies(query: HistoricalQuery):
    """
    Query historical anomalies from Parquet files
    Supports filtering by time range, source, destination, and score
    """
    if detector is None:
        raise HTTPException(status_code=503, detail="Detector not initialized")
    
    try:
        output_dir = detector.output_dir
        parquet_files = list(output_dir.glob('anomalies_*.parquet'))
        
        if not parquet_files:
            return AnomaliesResponse(count=0, anomalies=[])
        
        # Load all parquet files
        dfs = []
        for pf in parquet_files:
            try:
                df = pd.read_parquet(pf)
                dfs.append(df)
            except Exception as e:
                logger.warning(f"Error reading {pf}: {e}")
                continue
        
        if not dfs:
            return AnomaliesResponse(count=0, anomalies=[])
        
        # Combine all data
        all_anomalies = pd.concat(dfs, ignore_index=True)
        
        # Apply filters
        if query.start_time:
            all_anomalies = all_anomalies[
                all_anomalies['detected_at'] >= query.start_time
            ]
        
        if query.end_time:
            all_anomalies = all_anomalies[
                all_anomalies['detected_at'] <= query.end_time
            ]
        
        if query.src:
            all_anomalies = all_anomalies[all_anomalies['src'] == query.src]
        
        if query.dst:
            all_anomalies = all_anomalies[all_anomalies['dst'] == query.dst]
        
        if query.min_score is not None:
            all_anomalies = all_anomalies[
                all_anomalies['anomaly_score'] >= query.min_score
            ]
        
        # Limit results
        all_anomalies = all_anomalies.sort_values('detected_at', ascending=False)
        all_anomalies = all_anomalies.head(query.limit)
        
        # Convert to list of dicts
        results = all_anomalies.to_dict('records')
        
        return AnomaliesResponse(
            count=len(results),
            anomalies=results
        )
    
    except Exception as e:
        logger.error(f"Error querying historical anomalies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/anomalies/stats")
async def get_anomaly_stats():
    """Get anomaly detection statistics"""
    if detector is None:
        raise HTTPException(status_code=503, detail="Detector not initialized")
    
    try:
        output_dir = detector.output_dir
        parquet_files = list(output_dir.glob('anomalies_*.parquet'))
        
        if not parquet_files:
            return {
                "total_anomalies": detector.anomalies_detected,
                "files": 0,
                "by_source": {},
                "by_destination": {},
                "score_distribution": {}
            }
        
        # Load all data
        dfs = []
        for pf in parquet_files:
            try:
                df = pd.read_parquet(pf)
                dfs.append(df)
            except Exception as e:
                continue
        
        if not dfs:
            return {
                "total_anomalies": 0,
                "files": 0,
                "by_source": {},
                "by_destination": {},
                "score_distribution": {}
            }
        
        all_anomalies = pd.concat(dfs, ignore_index=True)
        
        # Compute statistics
        by_source = all_anomalies['src'].value_counts().to_dict()
        by_destination = all_anomalies['dst'].value_counts().to_dict()
        
        # Score distribution
        scores = all_anomalies['anomaly_score']
        score_dist = {
            "min": float(scores.min()),
            "max": float(scores.max()),
            "mean": float(scores.mean()),
            "median": float(scores.median()),
            "std": float(scores.std())
        }
        
        return {
            "total_anomalies": len(all_anomalies),
            "files": len(parquet_files),
            "by_source": by_source,
            "by_destination": by_destination,
            "score_distribution": score_dist
        }
    
    except Exception as e:
        logger.error(f"Error computing stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/control/retrain")
async def trigger_retraining():
    """
    Trigger model retraining (placeholder for future implementation)
    Would extract features from recent logs and retrain model
    """
    return {
        "status": "not_implemented",
        "message": "Model retraining will be implemented in future version"
    }


@app.get("/info/features")
async def get_feature_info():
    """Get information about features used in detection"""
    return {
        "num_features": 28,
        "window_seconds": detector.window_seconds if detector else 300,
        "features": [
            "value_mean_mean", "value_mean_std", "value_mean_min", "value_mean_max",
            "value_std_mean", "value_std_max",
            "value_range_mean", "value_range_max",
            "value_changes_sum", "value_change_rate_mean",
            "read_count_sum", "read_rate_mean",
            "inter_read_mean_mean", "inter_read_std_mean",
            "outlier_count_sum", "max_z_score_max",
            "unique_values_mean", "entropy_mean",
            "registers_accessed",
            "value_mean_mean_rolling_mean", "value_mean_mean_rolling_std", "value_mean_mean_deviation",
            "read_count_sum_rolling_mean", "read_count_sum_rolling_std", "read_count_sum_deviation",
            "value_change_rate_mean_rolling_mean", "value_change_rate_mean_rolling_std", "value_change_rate_mean_deviation"
        ],
        "description": "Behavioral features extracted from Modbus register patterns and temporal context"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
