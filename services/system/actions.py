import psutil
import logging
import json
from typing import Dict, Any

from services.system import config

logger = logging.getLogger(config.SERVICE_NAME)

def list_processes(params: Dict[str, Any]) -> str:
    """
    Lists running processes, optionally filtered by name.
    """
    try:
        process_list = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']):
            process_list.append(proc.info)
        
        # Optional filtering
        if "name" in params:
            process_list = [p for p in process_list if params["name"] in p["name"].lower()]
            
        return json.dumps({"status": "success", "data": process_list})
    except Exception as e:
        logger.error(f"Error listing processes: {e}")
        return json.dumps({"status": "error", "message": str(e)})

def kill_process(params: Dict[str, Any]) -> str:
    """
    Terminates a process by its PID.
    """
    pid = params.get("pid")
    if not pid:
        return json.dumps({"status": "error", "message": "PID must be provided."})

    try:
        process = psutil.Process(pid)
        process.terminate()  # or .kill() for a more forceful termination
        logger.info(f"Terminated process with PID {pid}")
        return json.dumps({"status": "success", "message": f"Process {pid} terminated."})
    except psutil.NoSuchProcess:
        return json.dumps({"status": "error", "message": f"No process with PID {pid} found."})
    except psutil.AccessDenied:
        return json.dumps({"status": "error", "message": f"Permission denied to terminate process {pid}."})
    except Exception as e:
        logger.error(f"Error killing process {pid}: {e}")
        return json.dumps({"status": "error", "message": str(e)})

# --- Action Dispatcher ---
# A mapping of action names to functions
ACTION_MAP = {
    "process.list": list_processes,
    "process.kill": kill_process,
}
