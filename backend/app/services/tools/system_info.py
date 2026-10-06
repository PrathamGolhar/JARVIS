import datetime
import os
import platform
import time
from typing import Any

import psutil


def get_system_diagnostics() -> dict[str, Any]:
    """
    Retrieve real-time hardware, operating system, and system resource diagnostics.
    """
    try:
        cpu_pct = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count(logical=True)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(os.path.abspath(os.sep))

        uptime_seconds = int(time.time() - psutil.boot_time())
        uptime_str = str(datetime.timedelta(seconds=uptime_seconds))

        battery = psutil.sensors_battery()
        battery_info = None
        if battery:
            battery_info = {
                "percent": battery.percent,
                "power_plugged": battery.power_plugged,
                "seconds_left": battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else "unlimited",
            }

        return {
            "ok": True,
            "os": f"{platform.system()} {platform.release()} ({platform.version()})",
            "processor": platform.processor() or platform.machine(),
            "cpu_usage_percent": cpu_pct,
            "cpu_cores": cpu_count,
            "ram_total_gb": round(memory.total / (1024**3), 2),
            "ram_used_gb": round(memory.used / (1024**3), 2),
            "ram_usage_percent": memory.percent,
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "disk_usage_percent": disk.percent,
            "system_uptime": uptime_str,
            "battery": battery_info,
        }
    except Exception as exc:
        return {"ok": False, "error": f"Unable to read system metrics: {exc}"}
