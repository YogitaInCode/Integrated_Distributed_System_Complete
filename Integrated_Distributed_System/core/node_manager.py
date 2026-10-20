"""Launch and stop local node processes for the Streamlit dashboard."""
from pathlib import Path
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
NODE_SCRIPT = ROOT / "nodes" / "node_server.py"
LOG_DIR = ROOT / "logs"
PROCESSES = {}


def start_node(node_id: int):
    existing = PROCESSES.get(node_id)
    if existing is not None and existing.poll() is None:
        return False, f"Node {node_id} process is already managed and running."

    LOG_DIR.mkdir(exist_ok=True)
    log_file = open(LOG_DIR / f"node{node_id}.log", "a", encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    process = subprocess.Popen(
        [sys.executable, str(NODE_SCRIPT), str(node_id)],
        cwd=str(ROOT),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env=env,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )
    PROCESSES[node_id] = process
    time.sleep(0.25)
    if process.poll() is not None:
        return False, f"Node {node_id} exited during startup. Check logs/node{node_id}.log."
    return True, f"Node {node_id} start command sent."


def start_all():
    results = []
    for node_id in (1, 2, 3):
        results.append(start_node(node_id))
    return results


def stop_node(node_id: int):
    process = PROCESSES.get(node_id)
    if process is None or process.poll() is not None:
        return False, f"No managed running process found for Node {node_id}."
    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)
    return True, f"Node {node_id} stopped."


def stop_all():
    return [stop_node(i) for i in (1, 2, 3)]
