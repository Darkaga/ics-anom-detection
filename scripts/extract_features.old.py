#!/usr/bin/env python3
"""
GPU-Accelerated Feature Extraction for ICS Anomaly Detection
Extracts temporal, statistical, and behavioral features from Zeek Modbus logs
"""

import argparse
import glob
import logging
from pathlib import Path
import sys
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import GPU libraries, fall back to CPU if needed
try:
    import cudf
    import cupy as cp
    USE_GPU = True
    logger.info("GPU acceleration enabled (RAPIDS cuDF)")
except ImportError:
    import pandas as pd
    import numpy as np
    USE_GPU = False
    logger.warning("RAPIDS not available, using CPU (pandas)")


def load_zeek_logs(log_pattern, use_gpu=True):
    """
    Load Zeek Modbus logs
    
    Args:
        log_pattern: Glob pattern for log files
        use_gpu: Whether to use GPU acceleration
    
    Returns:
        DataFrame with all logs combined
    """
    log_files = glob.glob(log_pattern)
    
    if not log_files:
        raise ValueError(f"No log files found matching pattern: {log_pattern}")
    
    logger.info(f"Found {len(log_files)} log files to process")
    
    dfs = []
    for log_file in sorted(log_files):
        logger.info(f"Loading {log_file}...")
        try:
            if use_gpu:
                df = cudf.read_json(log_file, lines=True)
            else:
                df = pd.read_json(log_file, lines=True)
            logger.info(f"  Loaded {len(df):,} records")
            dfs.append(df)
        except Exception as e:
            logger.error(f"  Error loading {log_file}: {e}")
            continue
    
    if not dfs:
        raise ValueError("No valid log files could be loaded")
    
    # Combine all dataframes
    if use_gpu:
        combined_df = cudf.concat(dfs, ignore_index=True)
    else:
        combined_df = pd.concat(dfs, ignore_index=True)
    
    logger.info(f"Total records loaded: {len(combined_df):,}")
    
    return combined_df


def extract_time_window_features(df, window_seconds=60, use_gpu=True):
    """
    Extract features aggregated over time windows
    """
    logger.info(f"Extracting time-window features (window={window_seconds}s)...")
    
    # Create time windows
    df['time_window'] = (df['ts'] // window_seconds).astype('int64')
    
    # Group by time window and source/destination pairs
    grouped = df.groupby(['time_window', 'id.orig_h', 'id.resp_h'])
    
    # Basic aggregations
    features = grouped.agg({
        'ts': ['count', 'min', 'max'],
        'tid': 'nunique',
        'unit': 'nunique',
        'id.orig_p': 'nunique',
    })
    
    # Flatten column names
    features.columns = ['_'.join(col).strip() for col in features.columns.values]
    features = features.reset_index()
    
    # Calculate derived features
    features['duration'] = features['ts_max'] - features['ts_min']
    features['transaction_rate'] = features['ts_count'] / window_seconds
    
    logger.info(f"Extracted {len(features):,} time-window feature vectors")
    logger.info(f"Feature dimensions: {features.shape[1]} features")
    
    return features


def extract_statistical_features(df, window_seconds=60, use_gpu=True):
    """
    Extract statistical features over time windows
    """
    logger.info("Extracting statistical features...")
    
    df['time_window'] = (df['ts'] // window_seconds).astype('int64')
    
    # Sort for inter-arrival time calculation
    df = df.sort_values(['id.orig_h', 'id.resp_h', 'ts'])
    
    # Calculate inter-arrival times
    df['inter_arrival_time'] = df.groupby(['id.orig_h', 'id.resp_h'])['ts'].diff()
    
    # Group and aggregate
    grouped = df.groupby(['time_window', 'id.orig_h', 'id.resp_h'])
    
    stats_features = grouped['inter_arrival_time'].agg([
        'mean', 'std', 'min', 'max'
    ]).reset_index()
    
    stats_features.columns = ['time_window', 'id.orig_h', 'id.resp_h',
                               'iat_mean', 'iat_std', 'iat_min', 'iat_max']
    
    # Fill NaN values
    stats_features = stats_features.fillna(0)
    
    logger.info(f"Extracted {len(stats_features):,} statistical feature vectors")
    
    return stats_features


def main():
    parser = argparse.ArgumentParser(
        description='Extract features from Zeek Modbus logs'
    )
    parser.add_argument(
        'log_pattern',
        help='Glob pattern for Zeek log files'
    )
    parser.add_argument(
        '--output',
        default='/workspace/data/features',
        help='Output directory for features'
    )
    parser.add_argument(
        '--window',
        type=int,
        default=60,
        help='Time window in seconds (default: 60)'
    )
    parser.add_argument(
        '--normalize',
        action='store_true',
        help='Normalize features (currently ignored, for compatibility)'
    )
    parser.add_argument(
        '--cpu',
        action='store_true',
        help='Force CPU mode even if GPU available'
    )
    
    args = parser.parse_args()
    
    # Determine if we should use GPU
    use_gpu = USE_GPU and not args.cpu
    
    if args.cpu:
        logger.info("CPU mode forced by --cpu flag")
    
    try:
        # Create output directory
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("="*70)
        logger.info(f"Feature Extraction Starting ({'GPU' if use_gpu else 'CPU'} mode)")
        logger.info("="*70)
        
        # Load logs
        df = load_zeek_logs(args.log_pattern, use_gpu)
        
        # Extract features
        time_features = extract_time_window_features(df, args.window, use_gpu)
        stats_features = extract_statistical_features(df, args.window, use_gpu)
        
        # Merge features
        logger.info("Merging feature sets...")
        all_features = time_features.merge(
            stats_features,
            on=['time_window', 'id.orig_h', 'id.resp_h'],
            how='left'
        )
        all_features = all_features.fillna(0)
        
        # Save features
        output_file = output_dir / 'features_time_windows.csv'
        
        logger.info(f"Saving features to {output_file}...")
        all_features.to_csv(output_file, index=False)
        
        # Save metadata
        metadata_file = output_dir / 'extraction_metadata.json'
        metadata = {
            'total_records': int(len(df)),
            'feature_vectors': int(len(all_features)),
            'num_features': int(all_features.shape[1]),
            'time_window_seconds': args.window,
            'gpu_accelerated': use_gpu,
            'output_file': str(output_file)
        }
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info("="*70)
        logger.info("Feature Extraction Complete!")
        logger.info("="*70)
        logger.info(f"Records processed: {len(df):,}")
        logger.info(f"Feature vectors: {len(all_features):,}")
        logger.info(f"Feature dimensions: {all_features.shape[1]}")
        logger.info(f"Output: {output_file}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Feature extraction failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
