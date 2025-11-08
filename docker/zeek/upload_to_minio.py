#!/usr/bin/env python3
"""
Upload Zeek logs to MinIO as they are rotated
"""

import os
import time
import logging
from pathlib import Path
from minio import Minio
from minio.error import S3Error
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configuration
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'localhost:9000').replace('http://', '').replace('https://', '')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'admin')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'minio123secure')
WATCH_DIR = '/zeek/logs'
BUCKET_NAME = 'zeek-logs'

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize MinIO client
try:
    minio_client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False
    )
    logger.info(f"Connected to MinIO at {MINIO_ENDPOINT}")
except Exception as e:
    logger.error(f"Failed to connect to MinIO: {e}")
    exit(1)

class ZeekLogHandler(FileSystemEventHandler):
    """Handle Zeek log file events"""
    
    def on_closed(self, event):
        """Upload file when it's closed (rotated)"""
        if event.is_directory:
            return
        
        filepath = Path(event.src_path)
        
        # Only upload .log files (Zeek rotated logs have timestamps)
        if filepath.suffix == '.log' and '-' in filepath.stem:
            self.upload_file(filepath)
    
    def upload_file(self, filepath):
        """Upload file to MinIO"""
        try:
            # Create object name with date structure
            object_name = f"{time.strftime('%Y/%m/%d')}/{filepath.name}"
            
            logger.info(f"Uploading {filepath.name} to {BUCKET_NAME}/{object_name}")
            
            minio_client.fput_object(
                BUCKET_NAME,
                object_name,
                str(filepath)
            )
            
            logger.info(f"Successfully uploaded {filepath.name}")
            
            # Optional: Remove local file after upload to save space
            # filepath.unlink()
            
        except S3Error as e:
            logger.error(f"Failed to upload {filepath.name}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error uploading {filepath.name}: {e}")

def main():
    """Main function"""
    logger.info(f"Starting Zeek log watcher on {WATCH_DIR}")
    logger.info(f"Uploading to bucket: {BUCKET_NAME}")
    
    # Create bucket if it doesn't exist
    try:
        if not minio_client.bucket_exists(BUCKET_NAME):
            minio_client.make_bucket(BUCKET_NAME)
            logger.info(f"Created bucket: {BUCKET_NAME}")
    except S3Error as e:
        logger.warning(f"Bucket check/creation issue: {e}")
    
    # Setup file watcher
    event_handler = ZeekLogHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIR, recursive=False)
    observer.start()
    
    logger.info("Watcher started. Press Ctrl+C to stop.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logger.info("Stopping watcher...")
    
    observer.join()

if __name__ == '__main__':
    main()
