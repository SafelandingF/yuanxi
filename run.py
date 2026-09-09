"""从仓库根目录启动本地前后端；Ctrl+C 同时停止。"""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    python = ROOT / (
        ".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python"
    )
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not python.exists() or not npm:
        print("请先按 README 安装 Python 虚拟环境与 Node.js 依赖。")
        return 1
    if not (ROOT / "config.yaml").exists():
        print("请复制 config.template.yaml 为 config.yaml 并填写 apikey。")
        return 1
    if not (ROOT / "frontend/node_modules").exists():
        print("请先在 frontend 目录执行 npm install。")
        return 1
    port = subprocess.run(
        [
            str(python),
            "-c",
            "from backend.core.config import load_settings; print(load_settings().port)",
        ],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    if port.returncode:
        print("配置读取失败，请检查 config.yaml。")
        return 1
    env = {**os.environ, "YUANXI_BACKEND_PORT": port.stdout.strip()}
    processes = []
    try:
        processes.append(subprocess.Popen([str(python), "-m", "backend"], cwd=ROOT))
        processes.append(
            subprocess.Popen(
                [npm, "run", "dev"],
                cwd=ROOT / "frontend",
                shell=os.name == "nt",
                env=env,
            )
        )
        print("缘析正在启动：http://127.0.0.1:5173 ；按 Ctrl+C 同时停止。", flush=True)
        while all(p.poll() is None for p in processes):
            time.sleep(0.5)
        print("有一个服务已退出，正在停止另一个服务。")
        return 1
    except KeyboardInterrupt:
        return 0
    finally:
        for p in processes:
            if p.poll() is None:
                p.terminate()
        for p in processes:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()


if __name__ == "__main__":
    sys.exit(main())
