#!/usr/bin/env python3
"""
Proper Anomaly Detection Training
Uses unsupervised learning to find REAL anomalies
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import argparse
import joblib
import logging
from pathlib import Path
import sys
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_and_prepare_features(features_path):
    """Load and prepare features for training"""
    logger.info(f"Loading features from {features_path}...")
    df = pd.read_csv(features_path)
    logger.info(f"Loaded {len(df):,} samples with {df.shape[1]} columns")
    
    # Separate metadata from features
    metadata_cols = ['time_window', 'src', 'dst']
    feature_cols = [col for col in df.columns if col not in metadata_cols]
    
    logger.info(f"Using {len(feature_cols)} features for training")
    
    X = df[feature_cols].values
    
    # Check for any remaining NaN/inf
    X = np.nan_to_num(X, nan=0.0, posinf=1e6, neginf=-1e6)
    
    return df, X, feature_cols


def normalize_features(X):
    """Normalize features - CRITICAL for Isolation Forest"""
    logger.info("Normalizing features...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    logger.info(f"Features normalized to mean=0, std=1")
    return X_scaled, scaler


def train_isolation_forest(X, contamination=0.01, n_estimators=100):
    """
    Train Isolation Forest with proper parameters
    
    Key insight: contamination should match expected anomaly rate
    If your system is mostly normal, use 0.01-0.05 (1-5%)
    """
    logger.info("Training Isolation Forest...")
    logger.info(f"  Expected anomaly rate: {contamination*100:.1f}%")
    logger.info(f"  Number of trees: {n_estimators}")
    logger.info(f"  This means ~{int(len(X) * contamination)} anomalies will be flagged")
    
    model = IsolationForest(
        contamination=contamination,
        n_estimators=n_estimators,
        max_samples='auto',
        random_state=42,
        n_jobs=-1,
        verbose=0
    )
    
    model.fit(X)
    
    # Get predictions
    predictions = model.predict(X)  # Returns 1 for normal, -1 for anomaly
    scores = model.score_samples(X)  # Lower (more negative) = more anomalous
    
    # Convert to 0/1 format (0=normal, 1=anomaly)
    anomalies = (predictions == -1).astype(int)
    n_anomalies = anomalies.sum()
    
    logger.info(f"Training complete!")
    logger.info(f"  Detected {n_anomalies} anomalies ({n_anomalies/len(X)*100:.2f}%)")
    logger.info(f"  Score range: {scores.min():.3f} to {scores.max():.3f}")
    logger.info(f"  More negative scores = more anomalous")
    
    return model, anomalies, scores


def analyze_anomalies(df, anomalies, scores, feature_cols):
    """Analyze what makes the anomalies anomalous"""
    logger.info("\nAnalyzing detected anomalies...")
    
    df['anomaly'] = anomalies
    df['anomaly_score'] = scores
    
    anomaly_df = df[df['anomaly'] == 1].copy()
    normal_df = df[df['anomaly'] == 0].copy()
    
    if len(anomaly_df) == 0:
        logger.warning("No anomalies detected!")
        return
    
    logger.info(f"\nTop 10 most anomalous samples:")
    logger.info(anomaly_df.nsmallest(10, 'anomaly_score')[
        ['time_window', 'src', 'dst', 'anomaly_score']
    ].to_string())
    
    # Find which features differ most
    logger.info(f"\nFeatures that differ most in anomalies vs normal:")
    
    feature_diffs = []
    for col in feature_cols:
        if col in df.columns:
            normal_mean = normal_df[col].mean()
            anomaly_mean = anomaly_df[col].mean()
            
            if normal_mean != 0:
                pct_diff = abs((anomaly_mean - normal_mean) / normal_mean) * 100
                feature_diffs.append((col, pct_diff, normal_mean, anomaly_mean))
    
    # Sort by difference
    feature_diffs.sort(key=lambda x: x[1], reverse=True)
    
    logger.info("\nTop 10 distinguishing features:")
    for feat, diff, norm, anom in feature_diffs[:10]:
        logger.info(f"  {feat:40s}: {diff:6.1f}% diff (normal={norm:.2f}, anomaly={anom:.2f})")


def save_results(df, output_path):
    """Save results with proper metadata"""
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save predictions
    output_file = output_dir / 'anomaly_detection_results.csv'
    logger.info(f"\nSaving results to {output_file}...")
    df.to_csv(output_file, index=False)
    
    # Save summary
    summary = {
        'total_samples': int(len(df)),
        'anomalies_detected': int(df['anomaly'].sum()),
        'anomaly_rate': float(df['anomaly'].sum() / len(df)),
        'mean_anomaly_score': float(df['anomaly_score'].mean()),
        'anomaly_score_range': [float(df['anomaly_score'].min()), 
                                float(df['anomaly_score'].max())],
        'most_anomalous_score': float(df['anomaly_score'].min()),
        
        # Time windows with anomalies
        'time_windows_with_anomalies': df[df['anomaly']==1]['time_window'].unique().tolist()[:20],
    }
    
    summary_file = output_dir / 'detection_summary.json'
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"Summary saved to {summary_file}")


def save_model(model, scaler, feature_names, output_path):
    """Save trained model for production use"""
    output_dir = Path(output_path)
    
    model_file = output_dir / 'anomaly_detector.pkl'
    logger.info(f"Saving model to {model_file}...")
    
    joblib.dump({
        'model': model,
        'scaler': scaler,
        'feature_names': feature_names
    }, model_file)
    
    logger.info("Model saved!")


def main():
    parser = argparse.ArgumentParser(
        description='Train anomaly detection model'
    )
    parser.add_argument(
        'features_path',
        help='Path to features CSV'
    )
    parser.add_argument(
        '--output',
        default='/workspace/data/models',
        help='Output directory'
    )
    parser.add_argument(
        '--contamination',
        type=float,
        default=0.01,
        help='Expected anomaly rate (0.01 = 1%%)'
    )
    parser.add_argument(
        '--n-estimators',
        type=int,
        default=100,
        help='Number of trees'
    )
    
    args = parser.parse_args()
    
    try:
        logger.info("="*70)
        logger.info("Anomaly Detection Training")
        logger.info("="*70)
        
        # Load features
        df, X, feature_cols = load_and_prepare_features(args.features_path)
        
        # Normalize (CRITICAL!)
        X_scaled, scaler = normalize_features(X)
        
        # Train
        model, anomalies, scores = train_isolation_forest(
            X_scaled, 
            args.contamination, 
            args.n_estimators
        )
        
        # Add results to dataframe
        df['anomaly'] = anomalies
        df['anomaly_score'] = scores
        
        # Analyze
        analyze_anomalies(df, anomalies, scores, feature_cols)
        
        # Save
        save_results(df, args.output)
        save_model(model, scaler, feature_cols, args.output)
        
        logger.info("\n" + "="*70)
        logger.info("Training Complete!")
        logger.info("="*70)
        logger.info(f"Results saved to: {args.output}")
        logger.info(f"\nTo investigate anomalies:")
        logger.info(f"  grep ',1,' {args.output}/anomaly_detection_results.csv")
        
        return 0
        
    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
