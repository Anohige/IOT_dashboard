# stats/system_stats.py

import psutil
import json

class SystemStats:
    """
    A class to gather system statistics.
    """
    def __init__(self):
        pass

    def get_system_stats(self):
        """Fetches system statistics from Raspberry Pi."""
        try:
            stats = {
                "cpu_usage": psutil.cpu_percent(interval=1),
                "ram_usage": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage("/").percent,
                "temperature": self.get_cpu_temperature()
            }
            return stats
        except Exception as e:
            print(f"[SystemStats] Error retrieving system stats: {e}")
            return {}

    def get_cpu_temperature(self):
        """Fetches CPU temperature from Raspberry Pi."""
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                return round(int(f.read()) / 1000, 2)
        except Exception as e:
            print(f"[SystemStats] Error getting CPU temperature: {e}")
            return None