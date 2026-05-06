# app/metrics_collector.py

import asyncio
import psutil
from datetime import datetime, timezone
import aiohttp
import os


class NoteMetricsCollector:
    service_name = "note-service"
    monitoring_url = os.getenv("MONITORING_URL", "http://localhost:8010")
    secret_key = os.getenv("NOTE_SERVICE_SECRET", "note_secret_key_2024")

    @staticmethod
    def collect() -> dict:
        """Collect CPU, memory, and thread metrics for the current process."""
        process = psutil.Process()
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cpu_usage": process.cpu_percent(interval=0.1),
            "memory_usage": process.memory_info().rss / 1024 / 1024,  # in MB
            "num_threads": process.num_threads(),
            "request_count": 1,  # You can customize or increment this dynamically
        }

    @classmethod
    async def run_loop(cls):
        """Optional legacy loop: periodically send metrics if not using `push_metrics_periodically`."""
        while True:
            try:
                metrics = cls.collect()

                headers = {
                    "X-Service-Secret": cls.secret_key,
                    "X-Service-Name": cls.service_name,
                    "Content-Type": "application/json"
                }

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{cls.monitoring_url}/api/v1/metrics",
                        json=metrics,
                        headers=headers
                    ) as response:
                        if response.status in [200, 201]:
                            print("✅ Sent metrics to monitoring-core")
                        else:
                            text = await response.text()
                            print(f"❌ Failed to send metrics: {response.status} - {text}")
            except Exception as e:
                print(f"⚠️ Metric push failed: {e}")

            await asyncio.sleep(30)
