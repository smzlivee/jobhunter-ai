#!/usr/bin/env python3
from __future__ import annotations

import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"


def _find_backend_python() -> Path:
    candidates = [
        BACKEND_DIR / ".venv" / "bin" / "python",
        BACKEND_DIR / ".venv" / "Scripts" / "python.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return Path(sys.executable)


def _require_cmd(name: str):
    if shutil.which(name) is None:
        raise RuntimeError(f"未找到命令: {name}")


def _ensure_backend_runtime(backend_python: Path):
    probe = subprocess.run(
        [str(backend_python), "-c", "import uvicorn"],
        cwd=BACKEND_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if probe.returncode != 0:
        raise RuntimeError("后端依赖未安装，请先执行: cd backend && uv sync")


def main():
    backend_proc = None
    frontend_proc = None

    def _cleanup():
        for proc in (backend_proc, frontend_proc):
            if proc and proc.poll() is None:
                proc.terminate()
        for proc in (backend_proc, frontend_proc):
            if not proc:
                continue
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()

    try:
        _require_cmd("npm")
        backend_python = _find_backend_python()
        _ensure_backend_runtime(backend_python)

        print("🚀 [1/3] 安装前端依赖（npm install）...")
        subprocess.run(["npm", "install"], cwd=FRONTEND_DIR, check=True)

        print("🚀 [2/3] 启动后端 (http://localhost:8000)...")
        backend_proc = subprocess.Popen(
            [str(backend_python), "-m", "uvicorn", "app.main:app", "--reload"],
            cwd=BACKEND_DIR,
        )

        print("🚀 [3/3] 启动前端 (http://localhost:3000)...")
        frontend_proc = subprocess.Popen(["npm", "run", "dev"], cwd=FRONTEND_DIR)

        print("✅ 已启动。按 Ctrl+C 统一停止前后端。")

        def _stop(*_):
            _cleanup()
            sys.exit(0)

        signal.signal(signal.SIGINT, _stop)
        signal.signal(signal.SIGTERM, _stop)

        while True:
            if backend_proc.poll() is not None:
                raise RuntimeError("后端进程已退出，请检查日志。")
            if frontend_proc.poll() is not None:
                raise RuntimeError("前端进程已退出，请检查日志。")
            time.sleep(1)
    except Exception as exc:
        _cleanup()
        print(f"❌ 启动失败: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
