#!/usr/bin/env python3
"""
Attack: Register Reconnaissance Scan
Rapidly scans all holding registers to map PLC memory layout
Expected Detection: High read frequency anomaly
"""

import sys
import time
from pymodbus.client import ModbusTcpClient

def run_attack(target_ip: str, duration: int = 30):
    """
    Perform aggressive register scanning
    
    Args:
        target_ip: Target PLC IP address
        duration: Attack duration in seconds
    """
    print(f"[*] Starting reconnaissance scan on {target_ip}")
    print(f"[*] Duration: {duration} seconds")
    print(f"[*] This will rapidly scan registers 0-999")
    
    client = ModbusTcpClient(target_ip, port=502, timeout=1)
    
    if not client.connect():
        print(f"[!] Failed to connect to {target_ip}")
        return {"status": "failed", "reason": "connection_failed"}
    
    print(f"[+] Connected to {target_ip}")
    
    start_time = time.time()
    scan_count = 0
    errors = 0
    
    try:
        while (time.time() - start_time) < duration:
            # Scan registers in blocks
            for start_addr in range(0, 1000, 10):
                try:
                    result = client.read_holding_registers(start_addr, count=10, slave=1)
                    if not result.isError():
                        scan_count += 10
                    else:
                        errors += 1
                    
                    # Very short delay to maximize scan rate
                    time.sleep(0.01)
                    
                except Exception as e:
                    errors += 1
                    continue
                
                # Check if duration exceeded
                if (time.time() - start_time) >= duration:
                    break
    
    finally:
        client.close()
        elapsed = time.time() - start_time
        
        print(f"\n[*] Scan complete!")
        print(f"[*] Registers scanned: {scan_count}")
        print(f"[*] Errors: {errors}")
        print(f"[*] Scan rate: {scan_count / elapsed:.1f} registers/sec")
        print(f"[*] Elapsed time: {elapsed:.1f} seconds")
        
        return {
            "status": "completed",
            "registers_scanned": scan_count,
            "errors": errors,
            "scan_rate": round(scan_count / elapsed, 2),
            "duration": round(elapsed, 2)
        }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python recon_scan.py <target_ip> [duration_seconds]")
        sys.exit(1)
    
    target = sys.argv[1]
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    
    run_attack(target, duration)
