
import re
import subprocess
import time


def get_default_gateway():
    """获取 Windows 系统默认 IPv4 网关。"""
    try:
        command = [
            "powershell",
            "-NoProfile",
            "-Command",
            (
                "Get-NetRoute -DestinationPrefix '0.0.0.0/0' "
                "| Sort-Object RouteMetric "
                "| Select-Object -First 1 "
                "-ExpandProperty NextHop"
            )
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10
        )

        return result.stdout.strip()

    except Exception as error:
        print("获取默认网关失败:", error)
        return None


def ping_host(host):
    """执行一次 Ping，返回网络检测结果。"""

    start = time.perf_counter()

    try:
        result = subprocess.run(
            ["ping", "-4", "-n", "1", "-w", "1000", host],
            capture_output=True,
            timeout=3,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        output = result.stdout.decode("gbk", errors="replace")

        match = re.search(
            r"(?:time|时间)\s*[=<]\s*(\d+)\s*ms",
            output,
            re.IGNORECASE
        )

        if result.returncode == 0 and match:
            return {
                "host": host,
                "success": True,
                "latency": float(match.group(1)),
                "timestamp": time.time()
            }

    except Exception as error:
        print("Ping 检测异常:", error)

    return {
        "host": host,
        "success": False,
        "latency": None,
        "timestamp": time.time()
    }
