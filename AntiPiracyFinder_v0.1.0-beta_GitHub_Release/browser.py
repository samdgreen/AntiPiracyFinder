import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from config import DEBUG_ADDRESS

def edge_debug_ready(timeout=1.2):
    try:
        with urllib.request.urlopen(
            f"http://{DEBUG_ADDRESS}/json/version", timeout=timeout
        ) as r:
            data = json.loads(r.read().decode("utf-8", errors="ignore"))
        return bool(data.get("webSocketDebuggerUrl"))
    except Exception:
        return False

def find_edge():
    candidates = [
        Path(os.environ.get("PROGRAMFILES(X86)", "")) /
        "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("PROGRAMFILES", "")) /
        "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) /
        "Microsoft/Edge/Application/msedge.exe",
    ]
    for p in candidates:
        if p.is_file():
            return str(p)
    return "msedge.exe"

def launch_edge(profile_dir):
    """
    启动专用于本工具的 Edge 调试窗口。
    不关闭用户日常 Edge，也不使用日常 Edge profile。
    """
    if edge_debug_ready():
        return False  # 已经启动，无需重复开

    Path(profile_dir).mkdir(parents=True, exist_ok=True)
    cmd = [
        find_edge(),
        "--remote-debugging-port=9222",
        "--remote-debugging-address=127.0.0.1",
        f"--user-data-dir={profile_dir}",
        "--new-window",
    ]
    subprocess.Popen(cmd)
    for _ in range(20):
        if edge_debug_ready():
            return True
        time.sleep(0.5)
    raise RuntimeError("Edge 已尝试启动，但未检测到调试端口。")

def attach_edge(retries=3):
    if not edge_debug_ready():
        raise RuntimeError("尚未启动本工具专用的 Edge。请先点击“启动 / 连接 Edge”。")
    last = None
    for _ in range(retries):
        try:
            options = Options()
            options.add_experimental_option("debuggerAddress", DEBUG_ADDRESS)
            return webdriver.Edge(options=options)
        except Exception as e:
            last = e
            time.sleep(1)
    raise RuntimeError(f"Edge 已启动，但程序连接失败：{last}")
