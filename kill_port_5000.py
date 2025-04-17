#!/usr/bin/env python3
import subprocess
import os
import signal

def find_processes_on_port(port):
    """
    Returns a list of process IDs (PIDs) that are listening on the specified port.
    """
    try:
        result = subprocess.check_output(["lsof", "-t", "-i", f":{port}"])
        pids = result.decode().split()
        return [int(pid) for pid in pids]
    except subprocess.CalledProcessError:
        # lsof returns non-zero exit code if no process is using the port
        return []

def kill_processes_on_port(port):
    """
    Kills all processes listening on the specified port.
    """
    pids = find_processes_on_port(port)
    if not pids:
        print(f"No process found on port {port}.")
        return
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Killed process {pid} on port {port}.")
        except Exception as e:
            print(f"Error killing process {pid}: {e}")

if __name__ == "__main__":
    port = 5000
    kill_processes_on_port(port)
