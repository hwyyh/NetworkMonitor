
import csv
import os
import time
import threading
from datetime import datetime
from statistics import mean

from src.network import ping_host, get_default_gateway


class NetworkMonitor:
    def __init__(self, public_ip="223.5.5.5", interval=1):
        self.gateway = get_default_gateway()
        self.public_ip = public_ip
        self.interval = interval

        self.running = False
        self.thread = None
        self.lock = threading.Lock()

        self.data = {
            "gateway": [],
            "public": []
        }

        self.log_dir = "logs"
        os.makedirs(self.log_dir, exist_ok=True)

        filename = datetime.now().strftime(
            "network_%Y%m%d_%H%M%S.csv"
        )
        self.log_path = os.path.join(
            self.log_dir, filename
        )

    def start(self):
        """开始网络监控。"""
        if self.running:
            return

        if not self.gateway:
            raise RuntimeError("无法获取默认网关")

        self.running = True

        self.thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        self.thread.start()

    def _monitor_loop(self):
        """持续检测网关和公网。"""
        with open(
            self.log_path,
            "w",
            newline="",
            encoding="utf-8-sig"
        ) as file:
            writer = csv.writer(file)
            writer.writerow([
                "timestamp",
                "target",
                "ip",
                "success",
                "latency_ms"
            ])

            while self.running:
                for target, ip in [
                    ("gateway", self.gateway),
                    ("public", self.public_ip)
                ]:
                    if not self.running:
                        break

                    result = ping_host(ip)

                    record = {
                        "timestamp": result["timestamp"],
                        "target": target,
                        "ip": ip,
                        "success": result["success"],
                        "latency": result["latency"]
                    }

                    with self.lock:
                        self.data[target].append(record)

                    writer.writerow([
                        record["timestamp"],
                        target,
                        ip,
                        record["success"],
                        record["latency"]
                    ])
                    file.flush()

                time.sleep(self.interval)

    def stop(self):
        """停止网络监控。"""
        self.running = False

        if self.thread:
            self.thread.join(timeout=8)

    def get_statistics(self, target):
        """获取指定目标的统计数据。"""
        with self.lock:
            records = list(self.data[target])

        if not records:
            return None

        latencies = [
            item["latency"]
            for item in records
            if item["success"] and item["latency"] is not None
        ]

        total = len(records)
        lost = total - len(latencies)
        loss_rate = lost / total * 100

        if not latencies:
            return {
                "total": total,
                "lost": lost,
                "loss_rate": loss_rate,
                "avg": None,
                "min": None,
                "max": None,
                "jitter": None
            }

        differences = [
            abs(latencies[i] - latencies[i - 1])
            for i in range(1, len(latencies))
        ]

        return {
            "total": total,
            "lost": lost,
            "loss_rate": loss_rate,
            "avg": mean(latencies),
            "min": min(latencies),
            "max": max(latencies),
            "jitter": mean(differences) if differences else 0
        }


if __name__ == "__main__":
    monitor = NetworkMonitor()

    print("默认网关:", monitor.gateway)
    print("公网目标:", monitor.public_ip)
    print("开始监控，持续 20 秒...")

    monitor.start()
    time.sleep(20)
    monitor.stop()

    print("\n===== 网络检测报告 =====")

    for target in ["gateway", "public"]:
        stats = monitor.get_statistics(target)

        print(f"\n目标: {target}")

        if stats is None:
            print("没有检测数据")
            continue

        for key, value in stats.items():
            print(f"{key}: {value}")

    print("\nCSV 日志:", monitor.log_path)
