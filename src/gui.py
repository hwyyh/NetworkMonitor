
import tkinter as tk
from tkinter import ttk, messagebox

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from src.monitor import NetworkMonitor


class NetworkMonitorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NetworkMonitor - 网络质量监测器")
        self.root.geometry("1000x720")
        self.root.minsize(780, 550)

        self.monitor = NetworkMonitor()
        self.closing = False

        self.status_var = tk.StringVar(value="未开始监控")
        self.gateway_var = tk.StringVar(value="-- ms")
        self.public_var = tk.StringVar(value="-- ms")
        self.gateway_stats = tk.StringVar(value="等待检测")
        self.public_stats = tk.StringVar(value="等待检测")

        self.create_widgets()
        self.root.after(1000, self.update_ui)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        container = ttk.Frame(self.root, padding=20)
        container.pack(fill="both", expand=True)

        ttk.Label(
            container,
            text="NetworkMonitor 网络质量监测器",
            font=("Microsoft YaHei UI", 19, "bold")
        ).pack(anchor="w", pady=(0, 12))

        ttk.Label(
            container,
            text=f"默认网关：{self.monitor.gateway}    "
                 f"公网目标：{self.monitor.public_ip}"
        ).pack(anchor="w")

        controls = ttk.Frame(container)
        controls.pack(fill="x", pady=15)

        self.start_button = ttk.Button(
            controls,
            text="开始监测",
            command=self.start_monitor
        )
        self.start_button.pack(side="left", padx=(0, 10))

        self.stop_button = ttk.Button(
            controls,
            text="停止监测",
            command=self.stop_monitor,
            state="disabled"
        )
        self.stop_button.pack(side="left")

        ttk.Label(
            controls,
            textvariable=self.status_var
        ).pack(side="right")

        info = ttk.Frame(container)
        info.pack(fill="x", pady=10)
        info.columnconfigure(0, weight=1)
        info.columnconfigure(1, weight=1)

        for index, (name, value, stats) in enumerate([
            ("路由器延迟", self.gateway_var, self.gateway_stats),
            ("公网延迟", self.public_var, self.public_stats)
        ]):
            panel = ttk.LabelFrame(info, text=name, padding=15)
            panel.grid(
                row=0,
                column=index,
                sticky="nsew",
                padx=5
            )

            ttk.Label(
                panel,
                textvariable=value,
                font=("Arial", 25, "bold")
            ).pack(anchor="w")

            ttk.Label(
                panel,
                textvariable=stats,
                wraplength=380
            ).pack(anchor="w", pady=(8, 0))

        chart_frame = ttk.LabelFrame(
            container,
            text="实时网络延迟曲线（最近100次检测）",
            padding=10
        )
        chart_frame.pack(
            fill="both",
            expand=True,
            pady=10
        )

        self.figure = Figure(figsize=(9, 4), dpi=100)
        self.ax = self.figure.add_subplot(111)

        self.canvas = FigureCanvasTkAgg(
            self.figure,
            master=chart_frame
        )
        self.canvas.get_tk_widget().pack(
            fill="both",
            expand=True
        )

        ttk.Label(
            container,
            text="说明：曲线断点表示探测失败；"
                 "数据来自实时 Ping 检测。"
        ).pack(anchor="w")

    def start_monitor(self):
        try:
            self.monitor.start()
        except Exception as error:
            messagebox.showerror("启动失败", str(error))
            return

        self.status_var.set("正在监控")
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")

    def stop_monitor(self):
        # 不阻塞界面等待 Ping 线程退出
        self.monitor.running = False
        self.status_var.set("正在停止...")
        self.stop_button.config(state="disabled")
        self.root.after(100, self.check_stopped)

    def check_stopped(self):
        thread = self.monitor.thread

        if thread is not None and thread.is_alive():
            self.root.after(100, self.check_stopped)
            return

        self.status_var.set(
            f"已停止，日志：{self.monitor.log_path}"
        )
        # 当前 Monitor 实例只使用一次。
        # 新监测会话创建新的实例和日志。
        self.monitor = NetworkMonitor()
        self.gateway_var.set("-- ms")
        self.public_var.set("-- ms")
        self.gateway_stats.set("等待检测")
        self.public_stats.set("等待检测")
        self.start_button.config(state="normal")

        if self.closing:
            self.root.destroy()

    def update_ui(self):
        if self.closing:
            return

        series = {}

        # 后台线程写入数据，GUI 只读取快照
        with self.monitor.lock:
            for target in ("gateway", "public"):
                series[target] = list(
                    self.monitor.data[target][-100:]
                )

        self.update_target("gateway", series["gateway"])
        self.update_target("public", series["public"])
        self.draw_chart(series)

        self.root.after(1000, self.update_ui)

    def update_target(self, target, records):
        value_var = (
            self.gateway_var if target == "gateway"
            else self.public_var
        )
        stats_var = (
            self.gateway_stats if target == "gateway"
            else self.public_stats
        )

        if not records:
            return

        latest = records[-1]["latency"]
        value_var.set(
            f"{latest:.1f} ms"
            if latest is not None else "超时"
        )

        stats = self.monitor.get_statistics(target)
        if not stats:
            return

        avg = stats["avg"]
        avg_text = f"{avg:.1f}" if avg is not None else "--"

        jitter = stats["jitter"]
        jitter_text = (
            f"{jitter:.1f}" if jitter is not None else "--"
        )

        stats_var.set(
            f"平均延迟：{avg_text} ms\n"
            f"丢包率：{stats['loss_rate']:.1f}%\n"
            f"延迟波动指标：{jitter_text} ms\n"
            f"检测次数：{stats['total']}"
        )

    def draw_chart(self, series):
        self.ax.clear()

        styles = [
            ("gateway", "Router", "#2563eb"),
            ("public", "Internet", "#16a34a")
        ]

        for key, label, color in styles:
            records = series[key]
            y = [
                record["latency"]
                if record["success"] else float("nan")
                for record in records
            ]
            self.ax.plot(
                range(len(y)),
                y,
                label=label,
                color=color,
                linewidth=1.8
            )

        self.ax.set_title("Network Latency")
        self.ax.set_xlabel("Sample")
        self.ax.set_ylabel("Latency (ms)")
        self.ax.set_xlim(0, 100)
        self.ax.set_ylim(bottom=0)
        self.ax.grid(alpha=0.25)
        self.ax.legend(loc="upper right")
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def on_close(self):
        self.closing = True
        thread = self.monitor.thread

        if thread is not None and thread.is_alive():
            self.stop_monitor()
        else:
            self.root.destroy()
