#!/usr/bin/env python3
"""
ML Training for ICS Anomaly Detection
Trains anomaly detection models with GPU acceleration when available
"""

import argparse
import logging
from pathlib import Path
import sys
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try GPU first, fall back to CPU
try:
    import cudf
    from cuml.ensemble import IsolationForest
    USE_GPU = True
    logger.info("GPU acceleration enabled (RAPIDS cuML)")
except ImportError:
    import pandas as pd
    from sklearn.ensemble import IsolationForest
    USE_GPU = False
    logger.warning("RAPIDS not available, using CPU (scikit-learn)")

import joblib


def load_features(features_path, use_gpu=True):
    """Load extracted features"""
    logger.info(f"Loading features from {features_path}...")
    
    if use_gpu:
        df = cudf.read_csv(features_path)
    else:
        df = pd.read_csv(features_path)
    
    logger.info(f"Loaded {len(df):,} feature vectors with {df.shape[1]} dimensions")
    return df


def prepare_training_data(df):
    """Prepare features for training"""
    logger.info("Preparing training data...")
    
    # Identify metadata columns to exclude
    metadata_cols = ['time_window', 'id.orig_h', 'id.resp_h', 'uid', 'timestamp']
    metadata_cols = [col for col in metadata_cols if col in df.columns]
    
    feature_cols = [col for col in df.columns if col not in metadata_cols]
    
    logger.info(f"Using {len(feature_cols)} features for training")
    
    X = df[feature_cols]
    
    return X, feature_cols


def train_isolation_forest(X, contamination=0.01, n_estimators=100, use_gpu=True):
    """Train Isolation Forest for anomaly detection"""
    logger.info("Training Isolation Forest...")
    logger.info(f"  Contamination: {contamination}")
    logger.info(f"  N estimators: {n_estimators}")
    logger.info(f"  Mode: {'GPU (cuML)' if use_gpu else 'CPU (scikit-learn)'}")
    
    if use_gpu:
        model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=42
        )
    else:
        model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=42,
            n_jobs=-1
        )
    
    model.fit(X)
    predictions = model.predict(X)
    scores = model.score_samples(X)
    
    # Convert predictions: -1 (anomaly) to 1, 1 (normal) to 0
    if use_gpu:
        anomalies = (predictions == -1).astype('int32')
        n_anomalies = int(anomalies.sum())
    else:
        anomalies = (predictions == -1).astype('int32')
        n_anomalies = int(anomalies.sum())
    
    logger.info(f"Training complete: {n_anomalies} anomalies detected ({n_anomalies/len(X)*100:.2f}%)")
    
    return model, anomalies, scores


def save_model(model, feature_names, output_path, model_name, metadata=None):
    """Save trained model"""
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    model_file = output_dir / f"{model_name}.pkl"
    logger.info(f"Saving model to {model_file}...")
    
    model_package = {
        'model': model,
        'feature_names': feature_names,
        'metadata': metadata or {}
    }
    
    joblib.dump(model_package, model_file)
    logger.info(f"Model saved successfully")


def save_results(df, predictions, scores, output_path, result_name, use_gpu=True):
    """Save prediction results"""
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Add predictions to dataframe
    results_df = df.copy()
    results_df['anomaly'] = predictions
    results_df['anomaly_score'] = scores
    
    output_file = output_dir / f"{result_name}_predictions.csv"
    logger.info(f"Saving results to {output_file}...")
    results_df.to_csv(output_file, index=False)
    
    # Save summary statistics
    summary_file = output_dir / f"{result_name}_summary.json"
    
    if use_gpu:
        summary = {
            'total_samples': int(len(results_df)),
            'anomalies_detected': int(predictions.sum()),
            'anomaly_rate': float(predictions.sum() / len(results_df)),
            'mean_anomaly_score': float(scores.mean()),
            'std_anomaly_score': float(scores.std())
        }
    else:
        summary = {
            'total_samples': int(len(results_df)),
            'anomalies_detected': int(predictions.sum()),
            'anomaly_rate': float(predictions.sum() / len(results_df)),
            'mean_anomaly_score': float(scores.mean()),
            'std_anomaly_score': float(scores.std())
        }
    
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"Results saved: {summary['anomalies_detected']} anomalies detected")


def main():
    parser = argparse.ArgumentParser(
        description='Train anomaly detection models'
    )
    parser.add_argument(
        'features_path',
        help='Path to features CSV file'
    )
    parser.add_argument(
        '--output',
        default='/workspace/data/models',
        help='Output directory for models'
    )
    parser.add_argument(
        '--contamination',
        type=float,
        default=0.01,
        help='Expected contamination rate (default: 0.01)'
    )
    parser.add_argument(
        '--n-estimators',
        type=int,
        default=100,
        help='Number of estimators (default: 100)'
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
        logger.info("="*70)
        logger.info(f"ML Training Starting ({'GPU' if use_gpu else 'CPU'} mode)")
        logger.info("="*70)
        
        # Load features
        df = load_features(args.features_path, use_gpu)
        X, feature_names = prepare_training_data(df)
        
        # Train model
        logger.info("\n" + "="*70)
        logger.info("Training Isolation Forest")
        logger.info("="*70)
        
        model, predictions, scores = train_isolation_forest(
            X,
            contamination=args.contamination,
            n_estimators=args.n_estimators,
            use_gpu=use_gpu
        )
        
        save_model(
            model, feature_names, args.output,
            'isolation_forest',
            metadata={
                'contamination': args.contamination,
                'n_estimators': args.n_estimators,
                'gpu_accelerated': use_gpu
            }
        )
        
        save_results(df, predictions, scores, args.output, 'isolation_forest', use_gpu)
        
        logger.info("\n" + "="*70)
        logger.info("Training Complete!")
        logger.info("="*70)
        logger.info(f"Models saved to: {args.output}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
