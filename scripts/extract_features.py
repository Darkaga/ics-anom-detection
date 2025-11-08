#!/usr/bin/env python3
"""
Advanced Feature Extraction for ICS Anomaly Detection
Uses register values, temporal patterns, and behavioral analysis
"""

import pandas as pd
import numpy as np
import argparse
import glob
import logging
from pathlib import Path
import sys
import json
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_detailed_logs(log_pattern):
    """Load modbus_detailed logs which have register values"""
    log_files = glob.glob(log_pattern)
    
    if not log_files:
        raise ValueError(f"No log files found: {log_pattern}")
    
    logger.info(f"Found {len(log_files)} detailed log files")
    
    dfs = []
    for log_file in sorted(log_files):
        logger.info(f"Loading {log_file}...")
        try:
            df = pd.read_json(log_file, lines=True)
            logger.info(f"  Loaded {len(df):,} records")
            dfs.append(df)
        except Exception as e:
            logger.error(f"  Error: {e}")
            continue
    
    combined_df = pd.concat(dfs, ignore_index=True)
    logger.info(f"Total records: {len(combined_df):,}")
    
    return combined_df


def extract_register_features(df, window_seconds=300):
    """
    Extract features based on register value patterns
    Key idea: Normal operations have consistent register patterns
    """
    logger.info(f"Extracting register features (window={window_seconds}s)...")
    
    # Parse response_values if they're strings
    if 'response_values' in df.columns:
        df['value_0'] = df['response_values'].apply(lambda x: x[0] if len(x) > 0 else 0)
        df['value_1'] = df['response_values'].apply(lambda x: x[1] if len(x) > 1 else 0)
    
    df['time_window'] = (df['ts'] // window_seconds).astype('int64')
    
    features_list = []
    
    # Group by device pair and address (each register)
    grouped = df.groupby(['time_window', 'id.orig_h', 'id.resp_h', 'address'])
    
    for (window, src, dst, addr), group in grouped:
        if len(group) < 3:  # Need enough samples
            continue
        
        # Register value statistics
        values = group['value_1'].values  # Main value typically in position 1
        
        feature = {
            'time_window': window,
            'src': src,
            'dst': dst,
            'address': addr,
            
            # Value statistics
            'value_mean': np.mean(values),
            'value_std': np.std(values),
            'value_min': np.min(values),
            'value_max': np.max(values),
            'value_range': np.max(values) - np.min(values),
            
            # Volatility (how much it changes)
            'value_changes': np.sum(np.diff(values) != 0),
            'value_change_rate': np.sum(np.diff(values) != 0) / len(values),
            
            # Read frequency
            'read_count': len(group),
            'read_rate': len(group) / window_seconds,
            
            # Timing statistics
            'inter_read_mean': np.mean(np.diff(group['ts'])),
            'inter_read_std': np.std(np.diff(group['ts'])) if len(group) > 2 else 0,
        }
        
        # Check for anomalous patterns
        # 1. Sudden value jumps (>3 std devs)
        if len(values) > 10:
            z_scores = np.abs((values - np.mean(values)) / (np.std(values) + 1e-6))
            feature['outlier_count'] = np.sum(z_scores > 3)
            feature['max_z_score'] = np.max(z_scores)
        else:
            feature['outlier_count'] = 0
            feature['max_z_score'] = 0
        
        # 2. Unusual value patterns (constant when should vary, or vice versa)
        feature['unique_values'] = len(np.unique(values))
        feature['entropy'] = -np.sum(np.histogram(values, bins=10)[0] / len(values) * 
                                     np.log(np.histogram(values, bins=10)[0] / len(values) + 1e-10))
        
        features_list.append(feature)
    
    features_df = pd.DataFrame(features_list)
    
    logger.info(f"Extracted {len(features_df):,} register-level feature vectors")
    
    return features_df


def aggregate_to_device_pairs(register_features):
    """
    Aggregate register features to device-pair level
    This gives us one feature vector per device pair per time window
    """
    logger.info("Aggregating to device-pair level...")
    
    grouped = register_features.groupby(['time_window', 'src', 'dst'])
    
    agg_features = grouped.agg({
        # Register statistics
        'value_mean': ['mean', 'std', 'min', 'max'],
        'value_std': ['mean', 'max'],
        'value_range': ['mean', 'max'],
        'value_changes': 'sum',
        'value_change_rate': 'mean',
        
        # Read patterns
        'read_count': 'sum',
        'read_rate': 'mean',
        'inter_read_mean': 'mean',
        'inter_read_std': 'mean',
        
        # Anomaly indicators
        'outlier_count': 'sum',
        'max_z_score': 'max',
        'unique_values': 'mean',
        'entropy': 'mean',
        
        # Number of registers accessed
        'address': 'nunique',
    })
    
    # Flatten column names
    agg_features.columns = ['_'.join(col).strip('_') for col in agg_features.columns]
    agg_features = agg_features.reset_index()
    
    # Rename for clarity
    agg_features = agg_features.rename(columns={'address_nunique': 'registers_accessed'})
    
    logger.info(f"Aggregated to {len(agg_features):,} device-pair feature vectors")
    
    return agg_features


def add_temporal_context(features_df):
    """
    Add temporal context - compare current window to recent history
    This is KEY for anomaly detection!
    """
    logger.info("Adding temporal context features...")
    
    features_df = features_df.sort_values(['src', 'dst', 'time_window'])
    
    # For each device pair, compute rolling statistics
    for (src, dst), group in features_df.groupby(['src', 'dst']):
        mask = (features_df['src'] == src) & (features_df['dst'] == dst)
        
        # Rolling window of last 5 time windows (for baseline)
        for col in ['value_mean_mean', 'read_count_sum', 'value_change_rate_mean']:
            if col in features_df.columns:
                rolling = features_df.loc[mask, col].rolling(window=5, min_periods=1)
                
                features_df.loc[mask, f'{col}_rolling_mean'] = rolling.mean()
                features_df.loc[mask, f'{col}_rolling_std'] = rolling.std()
                
                # Deviation from baseline
                baseline = rolling.mean().shift(1)  # Previous baseline
                features_df.loc[mask, f'{col}_deviation'] = (
                    (features_df.loc[mask, col] - baseline) / (baseline + 1)
                )
    
    features_df = features_df.fillna(0)
    
    logger.info("Temporal context added")
    
    return features_df


def main():
    parser = argparse.ArgumentParser(
        description='Extract advanced features for anomaly detection'
    )
    parser.add_argument(
        'log_pattern',
        help='Pattern for modbus_detailed log files'
    )
    parser.add_argument(
        '--output',
        default='/workspace/data/features',
        help='Output directory'
    )
    parser.add_argument(
        '--window',
        type=int,
        default=300,
        help='Time window in seconds (default: 300 = 5 minutes)'
    )
    
    args = parser.parse_args()
    
    try:
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("="*70)
        logger.info("Advanced Feature Extraction Starting")
        logger.info("="*70)
        
        # Load detailed logs (with register values)
        df = load_detailed_logs(args.log_pattern)
        
        # Extract register-level features
        register_features = extract_register_features(df, args.window)
        
        # Aggregate to device pairs
        device_features = aggregate_to_device_pairs(register_features)
        
        # Add temporal context (critical for anomaly detection!)
        final_features = add_temporal_context(device_features)
        
        # Save
        output_file = output_dir / 'features_advanced.csv'
        logger.info(f"Saving to {output_file}...")
        final_features.to_csv(output_file, index=False)
        
        # Save metadata
        metadata = {
            'total_records': int(len(df)),
            'feature_vectors': int(len(final_features)),
            'num_features': int(final_features.shape[1]),
            'time_window_seconds': args.window,
            'mode': 'Advanced behavioral analysis'
        }
        
        with open(output_dir / 'extraction_metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info("="*70)
        logger.info("Complete!")
        logger.info("="*70)
        logger.info(f"Feature vectors: {len(final_features):,}")
        logger.info(f"Feature dimensions: {final_features.shape[1]}")
        logger.info(f"Output: {output_file}")
        
        # Show feature names
        logger.info("\nFeatures extracted:")
        for col in final_features.columns:
            if col not in ['time_window', 'src', 'dst']:
                logger.info(f"  - {col}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
