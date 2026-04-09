#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp[cli]"]
# ///
"""
shellagent MCP Server — Local & Remote tmux-based agent infrastructure

Transparent, low-cost alternative to VM+Vision approaches.
All operations happen in tmux panes — humans see everything in real-time.

Two modes (set SHELLAGENT_MODE env var):
  - local:  Direct tmux commands + local file I/O (default)
  - remote: LOCAL_PANE relay + SSH for file ops

Usage:
    Registered in .mcp.json / .claude/settings.json as "shellagent" MCP server.
    Claude Code launches this automatically via stdio transport.
"""

import json
import logging
import os
import shlex
import subprocess
import time
import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

MODE = os.environ.get("SHELLAGENT_MODE", "local")  # "local" or "remote"
LOG_DIR = os.environ.get("SHELLAGENT_LOG_DIR", os.path.expanduser("~/.shellagent/logs"))

# Local mode settings
LOCAL_SESSION = os.environ.get("SHELLAGENT_SESSION", "shellagent")
LOCAL_WORKDIR = os.environ.get("SHELLAGENT_WORKDIR", os.path.expanduser("~"))

# Remote mode settings
REMOTE_HOST = os.environ.get("SHELLAGENT_REMOTE", "myserver")
REMOTE_SESSION = os.environ.get("SHELLAGENT_REMOTE_SESSION", "claude")
REMOTE_WORKDIR = os.environ.get("SHELLAGENT_REMOTE_WORKDIR", "/home/user/work")
REMOTE_VIEW_PANE = os.environ.get("SHELLAGENT_REMOTE_VIEW_PANE", "myserver:view.0")
REMOTE_TMUX_PREFIX = os.environ.get("SHELLAGENT_REMOTE_TMUX_PREFIX", "C-b")

IDLE_SHELLS = ("bash", "zsh", "sh", "tcsh", "csh", "fish")


# ──────────────────────────────────────────────
# Operation Logger — structured JSONL logging
# ──────────────────────────────────────────────

class OpLogger:
    """Logs all MCP tool calls to JSONL files."""

    def __init__(self, log_dir: str):
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._log_file = self._log_dir / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        self._seq = 0

    def log(self, tool: str, args: dict, result: str, duration_ms: int):
        self._seq += 1
        entry = {
            "seq": self._seq,
            "ts": datetime.now(timezone.utc).isoformat(),
            "tool": tool,
            "args": args,
            "result": result[:500] if isinstance(result, str) else str(result)[:500],
            "duration_ms": duration_ms,
        }
        with open(self._log_file, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    @property
    def log_path(self) -> str:
        return str(self._log_file)


op_logger = OpLogger(LOG_DIR)



# ──────────────────────────────────────────────
# Window Focus Helper
# ──────────────────────────────────────────────

def _focus_window(name: str):
    """Switch tmux focus to the named window so the user can see it."""
    try:
        session = LOCAL_SESSION if MODE == "local" else REMOTE_SESSION
        subprocess.run(
            ["tmux", "select-window", "-t", f"{session}:{name}"],
            check=False, timeout=5,
        )
    except Exception:
        pass


# ──────────────────────────────────────────────
# Transport Abstraction
# ──────────────────────────────────────────────


class Transport(ABC):
    """Abstract interface for tmux + file operations."""

    @abstractmethod
    def send_keys(self, target: str, *keys: str):
        """Send raw tmux keys to a pane."""

    @abstractmethod
    def send_literal(self, target: str, text: str):
        """Send literal text (no key interpretation)."""

    @abstractmethod
    def capture(self, target: str, lines: int = 50) -> str:
        """Capture pane output."""

    @abstractmethod
    def is_busy(self, target: str) -> bool:
        """Check if a pane has a foreground process running."""

    @abstractmethod
    def is_nvim_running(self, target: str) -> bool:
        """Check if nvim is running in the target pane."""

    @abstractmethod
    def read_file(self, path: str, offset: int = 1, limit: int = 300) -> str:
        """Read file contents with pagination."""

    @abstractmethod
    def write_file(self, path: str, content: str):
        """Write content to a file (create or overwrite)."""

    @abstractmethod
    def mkdir(self, path: str):
        """Create directory (and parents)."""

    @abstractmethod
    def file_exists(self, path: str) -> bool:
        """Check if a file exists."""

    @abstractmethod
    def line_count(self, path: str) -> int:
        """Get total line count of a file."""

    @abstractmethod
    def resolve_path(self, path: str) -> str:
        """Resolve relative path to absolute."""

    @abstractmethod
    def main_pane(self) -> str:
        """Return the main pane target string."""

    @abstractmethod
    def session_name(self) -> str:
        """Return the tmux session name."""

    @abstractmethod
    def workdir(self) -> str:
        """Return the working directory."""

    @abstractmethod
    def init_session(self) -> str:
        """Initialize the tmux session (idempotent)."""

    @abstractmethod
    def create_window(self, name: str):
        """Create a new tmux window."""

    @abstractmethod
    def send_to_window(self, name: str, cmd: str):
        """Send command to a named window."""

    @abstractmethod
    def capture_window(self, name: str, lines: int = 50) -> str:
        """Capture output from a named window."""

    @abstractmethod
    def is_window_busy(self, name: str) -> bool:
        """Check if a named window is busy."""

    @abstractmethod
    def kill_window_process(self, name: str):
        """Send C-c to a named window."""

    @abstractmethod
    def close_window(self, name: str):
        """Kill a named window."""

    @abstractmethod
    def list_windows(self) -> str:
        """List tmux windows."""

    # ── Shared helpers ──

    def send_cmd(self, target: str, cmd: str):
        """Send a command string with Enter."""
        self.send_literal(target, cmd)
        time.sleep(0.05)
        self.send_keys(target, "Enter")

    def escape_to_normal(self, target: str):
        """Send Escape twice to reliably enter normal mode."""
        self.send_keys(target, "Escape")
        time.sleep(0.1)
        self.send_keys(target, "Escape")
        time.sleep(0.1)

    def ensure_nvim(self, target: str):
        """Start nvim if not already running."""
        if not self.is_nvim_running(target):
            self.send_cmd(target, "nvim")
            for _ in range(10):
                time.sleep(0.3)
                if self.is_nvim_running(target):
                    return
            time.sleep(0.5)

    def exit_nvim(self, target: str) -> bool:
        """Force-exit nvim reliably."""
        if not self.is_nvim_running(target):
            return True
        # Triple Escape
        for _ in range(3):
            self.send_keys(target, "Escape")
            time.sleep(0.1)
        # :wa + :qa!
        self.send_literal(target, ":wa")
        self.send_keys(target, "Enter")
        time.sleep(0.1)
        self.send_keys(target, "Escape")
        time.sleep(0.05)
        self.send_literal(target, ":qa!")
        self.send_keys(target, "Enter")
        time.sleep(0.15)
        for _ in range(30):
            if not self.is_nvim_running(target):
                return True
            time.sleep(0.1)
        # Fallback: ZQ
        self.send_keys(target, "Escape")
        time.sleep(0.1)
        self.send_keys(target, "Z")
        time.sleep(0.05)
        self.send_keys(target, "Q")
        time.sleep(0.3)
        return not self.is_nvim_running(target)

    def nvim_cmd(self, target: str, cmd: str):
        """Send an Ex command to nvim."""
        self.ensure_nvim(target)
        self.escape_to_normal(target)
        self.send_literal(target, f":{cmd}")
        time.sleep(0.05)
        self.send_keys(target, "Enter")
        time.sleep(0.1)
        self.escape_to_normal(target)


# ──────────────────────────────────────────────
# Local Transport
# ──────────────────────────────────────────────


class LocalTransport(Transport):
    """Direct tmux operations on local machine."""

    def __init__(self):
        self._session = LOCAL_SESSION
        self._workdir = LOCAL_WORKDIR
        self._pane = f"{self._session}:main.0"

    def send_keys(self, target: str, *keys: str):
        subprocess.run(["tmux", "send-keys", "-t", target, *keys], check=False)

    def send_literal(self, target: str, text: str):
        if ";" not in text:
            subprocess.run(
                ["tmux", "send-keys", "-t", target, "-l", text], check=False
            )
        else:
            parts = text.split(";")
            for i, part in enumerate(parts):
                if part:
                    subprocess.run(
                        ["tmux", "send-keys", "-t", target, "-l", part], check=False
                    )
                if i < len(parts) - 1:
                    subprocess.run(
                        ["tmux", "send-keys", "-t", target, "-H", "3b"], check=False
                    )

    def capture(self, target: str, lines: int = 50) -> str:
        r = subprocess.run(
            ["tmux", "capture-pane", "-t", target, "-p", "-S", f"-{lines}"],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout

    def is_busy(self, target: str) -> bool:
        r = subprocess.run(
            ["tmux", "display-message", "-t", target, "-p",
             "#{pane_current_command}"],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip() not in IDLE_SHELLS

    def is_nvim_running(self, target: str) -> bool:
        r = subprocess.run(
            ["tmux", "display-message", "-t", target, "-p",
             "#{pane_current_command}"],
            capture_output=True, text=True, timeout=5,
        )
        cmd = r.stdout.strip()
        return cmd in ("nvim", "vim", "vi")

    def read_file(self, path: str, offset: int = 1, limit: int = 300) -> str:
        full = self.resolve_path(path)
        try:
            with open(os.path.expanduser(full), "r") as f:
                all_lines = f.readlines()
        except FileNotFoundError:
            return f"ERROR: File not found: {full}"
        except PermissionError:
            return f"ERROR: Permission denied: {full}"
        total = len(all_lines)
        if limit == 0:
            selected = all_lines
            start, end = 1, total
        else:
            start = offset
            end = min(offset + limit - 1, total)
            selected = all_lines[start - 1:end]
        numbered = "".join(
            f"{start + i:6d}  {line}" for i, line in enumerate(selected)
        )
        return f"{numbered}\n[Lines {start}-{end} of {total} total]"

    def write_file(self, path: str, content: str):
        full = os.path.expanduser(self.resolve_path(path))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(content)

    def mkdir(self, path: str):
        full = os.path.expanduser(self.resolve_path(path))
        os.makedirs(full, exist_ok=True)

    def file_exists(self, path: str) -> bool:
        full = os.path.expanduser(self.resolve_path(path))
        return os.path.exists(full)

    def line_count(self, path: str) -> int:
        full = os.path.expanduser(self.resolve_path(path))
        try:
            with open(full, "r") as f:
                return sum(1 for _ in f)
        except (FileNotFoundError, PermissionError):
            return 0

    def resolve_path(self, path: str) -> str:
        if path.startswith("/") or path.startswith("~/"):
            return path
        return f"{self._workdir}/{path}"

    def main_pane(self) -> str:
        return self._pane

    def session_name(self) -> str:
        return self._session

    def workdir(self) -> str:
        return self._workdir

    def init_session(self) -> str:
        r = subprocess.run(
            ["tmux", "has-session", "-t", self._session],
            capture_output=True,
        )
        if r.returncode != 0:
            subprocess.run(
                ["tmux", "new-session", "-d", "-s", self._session,
                 "-n", "main", "-c", self._workdir],
                check=False,
            )
            return f"Created new session '{self._session}'"
        return f"Session '{self._session}' already exists"

    def create_window(self, name: str):
        subprocess.run(
            ["tmux", "new-window", "-d", "-t", self._session,
             "-n", name, "-c", self._workdir],
            check=False,
        )

    def send_to_window(self, name: str, cmd: str):
        target = f"{self._session}:{name}"
        self.send_literal(target, cmd)
        self.send_keys(target, "Enter")

    def capture_window(self, name: str, lines: int = 50) -> str:
        target = f"{self._session}:{name}"
        return self.capture(target, lines)

    def is_window_busy(self, name: str) -> bool:
        target = f"{self._session}:{name}"
        return self.is_busy(target)

    def kill_window_process(self, name: str):
        target = f"{self._session}:{name}"
        self.send_keys(target, "C-c")

    def close_window(self, name: str):
        subprocess.run(
            ["tmux", "kill-window", "-t", f"{self._session}:{name}"],
            check=False,
        )

    def list_windows(self) -> str:
        r = subprocess.run(
            ["tmux", "list-windows", "-t", self._session],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout


# ──────────────────────────────────────────────
# Remote Transport
# ──────────────────────────────────────────────


class RemoteTransport(Transport):
    """Operates via LOCAL_PANE (SSH'd into remote) + SSH for file ops."""

    def __init__(self):
        self._remote = REMOTE_HOST
        self._session = REMOTE_SESSION
        self._workdir = REMOTE_WORKDIR
        self._local_pane = REMOTE_VIEW_PANE
        self._pane = f"{self._session}:ide.0"
        self._prefix = REMOTE_TMUX_PREFIX

    def _ssh(self, cmd: str, timeout: int = 30, input_text: str | None = None) -> str:
        r = subprocess.run(
            ["ssh", self._remote, cmd],
            capture_output=True, text=True, timeout=timeout,
            input=input_text,
        )
        lines = r.stdout.splitlines()
        filtered = [l for l in lines
                     if not re.match(r'^\s*(Loading |WARNING|requirement)', l)]
        return "\n".join(filtered)

    def _rtmux(self, *args: str, timeout: int = 10) -> str:
        cmd = f"tmux {' '.join(args)}"
        return self._ssh(cmd, timeout=timeout)

    def send_keys(self, target: str, *keys: str):
        if target == self._pane:
            subprocess.run(
                ["tmux", "send-keys", "-t", self._local_pane, *keys],
                check=False,
            )
        else:
            self._rtmux("send-keys", "-t", target, *keys)

    def send_literal(self, target: str, text: str):
        if target == self._pane:
            if ";" not in text:
                subprocess.run(
                    ["tmux", "send-keys", "-t", self._local_pane, "-l", text],
                    check=False,
                )
            else:
                parts = text.split(";")
                for i, part in enumerate(parts):
                    if part:
                        subprocess.run(
                            ["tmux", "send-keys", "-t", self._local_pane, "-l", part],
                            check=False,
                        )
                    if i < len(parts) - 1:
                        subprocess.run(
                            ["tmux", "send-keys", "-t", self._local_pane, "-H", "3b"],
                            check=False,
                        )
        else:
            self._rtmux("send-keys", "-t", target, "-l", shlex.quote(text))

    def capture(self, target: str, lines: int = 50) -> str:
        if target == self._pane:
            r = subprocess.run(
                ["tmux", "capture-pane", "-t", self._local_pane,
                 "-p", "-S", f"-{lines}"],
                capture_output=True, text=True, timeout=5,
            )
            return r.stdout
        return self._rtmux("capture-pane", "-t", target, "-p", "-S", f"-{lines}")

    def is_busy(self, target: str) -> bool:
        if target == self._pane:
            output = self.capture(target, 5)
            last = ""
            for line in reversed(output.splitlines()):
                if line.strip():
                    last = line.strip()
                    break
            return not (last.endswith("$") or last.endswith("%"))
        pane_cmd = self._rtmux(
            "display-message", "-t", target, "-p", "'#{pane_current_command}'"
        )
        return pane_cmd.strip() not in IDLE_SHELLS

    def is_nvim_running(self, target: str) -> bool:
        output = self.capture(target, 5)
        if not output:
            return False
        if re.search(r'-- (INSERT|VISUAL|REPLACE)', output):
            return True
        lines = output.strip().splitlines()
        for line in lines[-3:]:
            if re.search(r'\d+,\d+\s+(All|Top|Bot|\d+%)', line):
                return True
        return False

    def read_file(self, path: str, offset: int = 1, limit: int = 300) -> str:
        full = self.resolve_path(path)
        total = self._ssh(f"wc -l < {full}").strip()
        if limit == 0:
            result = self._ssh(f"cat -n {full}", timeout=60)
        else:
            end = offset + limit - 1
            result = self._ssh(
                f"awk 'NR>={offset} && NR<={end} {{printf \"%6d  %s\\n\", NR, $0}}' {full}"
            )
        shown_end = total if limit == 0 else str(min(offset + limit - 1, int(total)))
        return f"{result}\n\n[Lines {offset}-{shown_end} of {total} total]"

    def write_file(self, path: str, content: str):
        full = self.resolve_path(path)
        self._ssh(f"mkdir -p $(dirname {full})")
        subprocess.run(
            ["ssh", self._remote, f"cat > {full}"],
            input=content, text=True, check=False,
        )

    def mkdir(self, path: str):
        full = self.resolve_path(path)
        self._ssh(f"mkdir -p {full}")

    def file_exists(self, path: str) -> bool:
        full = self.resolve_path(path)
        result = self._ssh(f"test -e {full} && echo yes || echo no")
        return result.strip() == "yes"

    def line_count(self, path: str) -> int:
        full = self.resolve_path(path)
        result = self._ssh(f"wc -l < {full}").strip()
        try:
            return int(result)
        except ValueError:
            return 0

    def resolve_path(self, path: str) -> str:
        if path.startswith("/") or path.startswith("~/"):
            return path
        return f"{self._workdir}/{path}"

    def main_pane(self) -> str:
        return self._pane

    def session_name(self) -> str:
        return self._session

    def workdir(self) -> str:
        return self._workdir

    def init_session(self) -> str:
        self._ssh(
            f"tmux has-session -t {self._session} 2>/dev/null || "
            f"tmux new-session -d -s {self._session} -n ide -c {self._workdir}"
        )
        local_session = self._local_pane.split(":")[0]
        r = subprocess.run(
            ["tmux", "has-session", "-t", local_session],
            capture_output=True,
        )
        if r.returncode != 0:
            return (
                f"ERROR: Local tmux session '{local_session}' not found. "
                f"Run: tmux new -d -s {local_session}"
            )
        return "Remote session initialized"

    def _local_pane_state(self) -> str:
        r = subprocess.run(
            ["tmux", "display-message", "-t", self._local_pane, "-p",
             "#{pane_current_command}"],
            capture_output=True, text=True, timeout=5,
        )
        current_cmd = r.stdout.strip()
        if current_cmd != "ssh":
            return "local_shell"
        output = self.capture(self._pane, 3)
        if f"Session: {self._session}" in output:
            return "remote_tmux"
        return "remote_shell"

    def _detach_remote(self):
        state = self._local_pane_state()
        if state == "remote_tmux":
            subprocess.run(
                ["tmux", "send-keys", "-t", self._local_pane, self._prefix],
                check=False,
            )
            time.sleep(0.2)
            subprocess.run(
                ["tmux", "send-keys", "-t", self._local_pane, "d"],
                check=False,
            )
            time.sleep(0.5)
        elif state == "local_shell":
            subprocess.run(
                ["tmux", "send-keys", "-t", self._local_pane, "-l",
                 f"TERM=xterm-256color ssh -t {self._remote}"],
                check=False,
            )
            subprocess.run(
                ["tmux", "send-keys", "-t", self._local_pane, "Enter"],
                check=False,
            )
            time.sleep(3)

    def _attach_remote(self):
        state = self._local_pane_state()
        if state == "remote_tmux":
            return
        if state == "remote_shell":
            subprocess.run(
                ["tmux", "send-keys", "-t", self._local_pane, "-l",
                 f"tmux attach -t {self._session}"],
                check=False,
            )
            subprocess.run(
                ["tmux", "send-keys", "-t", self._local_pane, "Enter"],
                check=False,
            )
            time.sleep(0.3)
        elif state == "local_shell":
            subprocess.run(
                ["tmux", "send-keys", "-t", self._local_pane, "-l",
                 f"TERM=xterm-256color ssh -t {self._remote}"],
                check=False,
            )
            subprocess.run(
                ["tmux", "send-keys", "-t", self._local_pane, "Enter"],
                check=False,
            )
            time.sleep(3)
            subprocess.run(
                ["tmux", "send-keys", "-t", self._local_pane, "-l",
                 f"tmux attach -t {self._session}"],
                check=False,
            )
            subprocess.run(
                ["tmux", "send-keys", "-t", self._local_pane, "Enter"],
                check=False,
            )
            time.sleep(0.3)

    def _remote_shell_cmd(self, cmd: str):
        self._detach_remote()
        subprocess.run(
            ["tmux", "send-keys", "-t", self._local_pane, "-l", cmd],
            check=False,
        )
        subprocess.run(
            ["tmux", "send-keys", "-t", self._local_pane, "Enter"],
            check=False,
        )
        time.sleep(0.2)
        self._attach_remote()

    def create_window(self, name: str):
        self._remote_shell_cmd(
            f"tmux new-window -d -n {name} -c {self._workdir}"
        )

    def send_to_window(self, name: str, cmd: str):
        self._remote_shell_cmd(
            f"tmux send-keys -t :{name} -l {shlex.quote(cmd)}"
        )
        self._remote_shell_cmd(f"tmux send-keys -t :{name} Enter")

    def capture_window(self, name: str, lines: int = 50) -> str:
        self._detach_remote()
        subprocess.run(
            ["tmux", "send-keys", "-t", self._local_pane, "-l",
             f"tmux capture-pane -t :{name} -p -S -{lines}"],
            check=False,
        )
        subprocess.run(
            ["tmux", "send-keys", "-t", self._local_pane, "Enter"],
            check=False,
        )
        time.sleep(0.3)
        r = subprocess.run(
            ["tmux", "capture-pane", "-t", self._local_pane,
             "-p", "-S", f"-{lines + 5}"],
            capture_output=True, text=True, timeout=5,
        )
        self._attach_remote()
        return r.stdout

    def is_window_busy(self, name: str) -> bool:
        output = self.capture_window(name, 5)
        last = ""
        for line in reversed(output.splitlines()):
            if line.strip():
                last = line.strip()
                break
        return not (last.endswith("$") or last.endswith("%"))

    def kill_window_process(self, name: str):
        self._remote_shell_cmd(f"tmux send-keys -t :{name} C-c")

    def close_window(self, name: str):
        self._remote_shell_cmd(f"tmux kill-window -t :{name}")

    def list_windows(self) -> str:
        self._detach_remote()
        subprocess.run(
            ["tmux", "send-keys", "-t", self._local_pane, "-l", "tmux list-windows"],
            check=False,
        )
        subprocess.run(
            ["tmux", "send-keys", "-t", self._local_pane, "Enter"],
            check=False,
        )
        time.sleep(0.3)
        r = subprocess.run(
            ["tmux", "capture-pane", "-t", self._local_pane, "-p", "-S", "-20"],
            capture_output=True, text=True, timeout=5,
        )
        self._attach_remote()
        return r.stdout


# ──────────────────────────────────────────────
# Transport selection
# ──────────────────────────────────────────────

transport: Transport
if MODE == "remote":
    transport = RemoteTransport()
else:
    transport = LocalTransport()


# ──────────────────────────────────────────────
# MCP Server
# ──────────────────────────────────────────────

mcp = FastMCP("shellagent")


# ── Logging: hook into FastMCP's call_tool ──
_original_call_tool = mcp._tool_manager.call_tool.__func__ if hasattr(mcp._tool_manager.call_tool, '__func__') else None


async def _logged_call_tool(self, name, arguments, **kwargs):
    """Wrap ToolManager.call_tool to auto-log every MCP call."""
    t0 = time.time()
    try:
        result = await _original_call_tool(self, name, arguments, **kwargs) if _original_call_tool else await type(self).call_tool(self, name, arguments, **kwargs)
        duration = int((time.time() - t0) * 1000)
        result_text = ""
        if result:
            for item in result:
                if hasattr(item, 'text'):
                    result_text += item.text
        op_logger.log(name, arguments or {}, result_text, duration)
        return result
    except Exception as e:
        duration = int((time.time() - t0) * 1000)
        op_logger.log(name, arguments or {}, f"ERROR: {e}", duration)
        raise


# Monkey-patch the tool manager
import types
mcp._tool_manager.call_tool = types.MethodType(_logged_call_tool, mcp._tool_manager)


# ──────────────────────────────────────────────
# Session Management
# ──────────────────────────────────────────────


@mcp.tool()
def init() -> str:
    """Initialize the tmux session (idempotent). Call this first."""
    return transport.init_session()


@mcp.tool()
def status() -> str:
    """Show session status: all windows, all panes, and their processes."""
    session = transport.session_name()
    windows = transport.list_windows()

    # Get detailed pane info for all panes in the session
    r = subprocess.run(
        ["tmux", "list-panes", "-t", session, "-a",
         "-F", "#{window_name}:#{pane_index} #{pane_id} #{pane_width}x#{pane_height} #{pane_current_command}"],
        capture_output=True, text=True, timeout=5,
    )
    pane_info = r.stdout.strip() if r.returncode == 0 else "(unable to list panes)"

    return (
        f"Session: {session}\n"
        f"Mode: {MODE}\n"
        f"Workdir: {transport.workdir()}\n"
        f"Log: {op_logger.log_path}\n"
        f"\nWindows:\n{windows}\n"
        f"Panes:\n{pane_info}"
    )


# ──────────────────────────────────────────────
# Terminal — Main pane
# ──────────────────────────────────────────────


@mcp.tool()
def run(cmd: str) -> str:
    """Execute a command in the main pane. Auto-closes nvim if open."""
    _focus_window("main")
    pane = transport.main_pane()
    if transport.is_nvim_running(pane):
        if not transport.exit_nvim(pane):
            return "ERROR: Could not close nvim. Force quit manually."
        time.sleep(0.15)
    transport.send_cmd(pane, cmd)
    return f"Sent: {cmd}"


@mcp.tool()
def run_output(lines: int = 50) -> str:
    """Capture recent output from the main pane."""
    return transport.capture(transport.main_pane(), lines)


@mcp.tool()
def run_busy() -> bool:
    """Check if the main pane is running a foreground process."""
    return transport.is_busy(transport.main_pane())


@mcp.tool()
def run_kill() -> str:
    """Send Ctrl+C to the main pane."""
    transport.send_keys(transport.main_pane(), "C-c")
    return "Sent Ctrl+C"


# ──────────────────────────────────────────────
# File Editing (via nvim)
# ──────────────────────────────────────────────


@mcp.tool()
def open_file(path: str) -> str:
    """Open file in nvim. Accepts absolute (~/ or /) or relative (to workdir) paths."""
    _focus_window("main")
    full = transport.resolve_path(path)
    transport.nvim_cmd(transport.main_pane(), f"e {full}")
    return f"Opened {full}"


@mcp.tool()
def goto_line(n: int) -> str:
    """Jump to line number n in the current nvim buffer."""
    transport.nvim_cmd(transport.main_pane(), str(n))
    return f"Jumped to line {n}"


@mcp.tool()
def replace(old: str, new: str, flags: str = "g") -> str:
    """Single-line substitution in the current nvim buffer.
    For multi-line, use delete_lines() + bulk_insert()."""
    pane = transport.main_pane()
    o = old.replace("/", "\\/")
    n = new.replace("/", "\\/")
    transport.ensure_nvim(pane)
    transport.escape_to_normal(pane)
    # Jump to top
    transport.send_keys(pane, "g")
    time.sleep(0.02)
    transport.send_keys(pane, "g")
    time.sleep(0.1)
    # Search for the text
    transport.send_literal(pane, f"/\\V{o}")
    transport.send_keys(pane, "Enter")
    time.sleep(0.2)
    # Replace on current line
    transport.nvim_cmd(pane, f"s/\\V{o}/{n}/{flags}")
    return f"Replaced '{old[:50]}' -> '{new[:50]}'"


@mcp.tool()
def delete_lines(start: int, end: int) -> str:
    """Delete a range of lines in the current nvim buffer."""
    transport.nvim_cmd(transport.main_pane(), f"{start},{end}d")
    return f"Deleted lines {start}-{end}"


@mcp.tool()
def insert_after(line: int, text: str) -> str:
    """Insert text after the given line number."""
    pane = transport.main_pane()
    full = transport.resolve_path("~/.shellagent_insert_tmp")
    transport.write_file(full, text)
    transport.nvim_cmd(pane, f"{line}r {full}")
    return f"Inserted text after line {line}"


@mcp.tool()
def bulk_insert(line: int, text: str) -> str:
    """Insert a large block of text after the given line using paste mode.
    WARNING: line=0 is unreliable. Use line >= 1 only."""
    pane = transport.main_pane()
    transport.ensure_nvim(pane)
    transport.nvim_cmd(pane, str(line))
    time.sleep(0.05)
    transport.nvim_cmd(pane, "set paste")
    time.sleep(0.05)
    transport.send_keys(pane, "Escape")
    time.sleep(0.05)
    transport.send_keys(pane, "o")
    time.sleep(0.05)
    for i, chunk_line in enumerate(text.split("\n")):
        if i > 0:
            transport.send_keys(pane, "Enter")
            time.sleep(0.02)
        transport.send_literal(pane, chunk_line)
        time.sleep(0.02)
    time.sleep(0.2)
    transport.escape_to_normal(pane)
    transport.nvim_cmd(pane, "set nopaste")
    return f"Inserted {len(text.splitlines())} lines after line {line}"


@mcp.tool()
def write_new_file(path: str, content: str) -> str:
    """Create a new file with the given content."""
    full = transport.resolve_path(path)
    transport.write_file(full, content)
    return f"Created {full}"


@mcp.tool()
def read_file(path: str, offset: int = 1, limit: int = 300) -> str:
    """Read file contents with line numbers. Supports pagination.
    Args:
        path: File path (absolute or relative to workdir)
        offset: Starting line number (1-based, default 1)
        limit: Number of lines to read (default 300, 0=all)
    """
    return transport.read_file(path, offset, limit)


@mcp.tool()
def commit_edit(path: str, summary: str) -> dict:
    """Save file in nvim and report the edit."""
    transport.nvim_cmd(transport.main_pane(), "w")
    time.sleep(0.1)
    return {"path": path, "summary": summary, "status": "saved"}


# ──────────────────────────────────────────────
# Tab Management (nvim tabs)
# ──────────────────────────────────────────────


@mcp.tool()
def tab_open(path: str) -> str:
    """Open file in a new nvim tab."""
    full = transport.resolve_path(path)
    transport.nvim_cmd(transport.main_pane(), f"tabedit {full}")
    return f"Opened {full} in new tab"


@mcp.tool()
def tab_list() -> str:
    """List open nvim tabs."""
    pane = transport.main_pane()
    transport.nvim_cmd(pane, "tabs")
    time.sleep(0.2)
    return transport.capture(pane, 20)


@mcp.tool()
def tab_switch(n: int) -> str:
    """Switch to the nth nvim tab (1-indexed)."""
    transport.nvim_cmd(transport.main_pane(), f"tabn {n}")
    return f"Switched to tab {n}"


@mcp.tool()
def tab_next() -> str:
    """Switch to the next nvim tab."""
    transport.nvim_cmd(transport.main_pane(), "tabnext")
    return "Next tab"


@mcp.tool()
def tab_prev() -> str:
    """Switch to the previous nvim tab."""
    transport.nvim_cmd(transport.main_pane(), "tabprev")
    return "Previous tab"


@mcp.tool()
def tab_close() -> str:
    """Close the current nvim tab."""
    transport.nvim_cmd(transport.main_pane(), "tabclose")
    return "Tab closed"


# ──────────────────────────────────────────────
# Terminal — Parallel sessions (windows)
# ──────────────────────────────────────────────


@mcp.tool()
def term_new(name: str) -> str:
    """Create a new tmux window for parallel work."""
    transport.create_window(name)
    return f"Created window '{name}'"


@mcp.tool()
def term_send(name: str, cmd: str) -> str:
    """Send a command to a named tmux window."""
    transport.send_to_window(name, cmd)
    return f"Sent to '{name}': {cmd}"


@mcp.tool()
def term_output(name: str, lines: int = 50) -> str:
    """Capture recent output from a named tmux window."""
    return transport.capture_window(name, lines)


@mcp.tool()
def term_busy(name: str) -> bool:
    """Check if a named window has a running process."""
    return transport.is_window_busy(name)


@mcp.tool()
def term_kill(name: str) -> str:
    """Send Ctrl+C to a named window."""
    transport.kill_window_process(name)
    return f"Sent Ctrl+C to '{name}'"


@mcp.tool()
def term_close(name: str) -> str:
    """Kill a named tmux window."""
    transport.close_window(name)
    return f"Closed window '{name}'"


@mcp.tool()
def term_list() -> str:
    """List all tmux windows in the session."""
    return transport.list_windows()


# ──────────────────────────────────────────────
# Pane Management (split panes for agents)
# ──────────────────────────────────────────────

# Track named panes: name -> pane_id (e.g. "%5")
_pane_registry: dict[str, str] = {}


def _pane_target(name: str) -> str | None:
    """Get tmux pane target for a named pane."""
    pane_id = _pane_registry.get(name)
    if not pane_id:
        return None
    # Verify it still exists
    r = subprocess.run(
        ["tmux", "list-panes", "-t", transport.session_name(),
         "-F", "#{pane_id}", "-a"],
        capture_output=True, text=True, timeout=5,
    )
    if pane_id not in r.stdout.splitlines():
        del _pane_registry[name]
        return None
    return pane_id


@mcp.tool()
def pane_split(name: str, direction: str = "horizontal", size: int = 50) -> str:
    """Split the main window to create a named pane for an agent.
    Args:
        name: Name for the new pane (used to reference it later)
        direction: 'horizontal' (side by side) or 'vertical' (top/bottom)
        size: Percentage of space for the new pane (default 50)
    """
    if name in _pane_registry and _pane_target(name):
        return f"Pane '{name}' already exists"
    flag = "-h" if direction == "horizontal" else "-v"
    main = transport.main_pane()
    r = subprocess.run(
        ["tmux", "split-window", flag, "-t", main,
         "-p", str(size), "-d",  # -d: don't switch focus
         "-c", transport.workdir(),
         "-P", "-F", "#{pane_id}"],  # print new pane id
        capture_output=True, text=True, timeout=5,
    )
    pane_id = r.stdout.strip()
    if not pane_id:
        return "ERROR: Failed to split pane"
    _pane_registry[name] = pane_id
    return f"Created pane '{name}' ({pane_id}, {direction}, {size}%)"


@mcp.tool()
def pane_send(name: str, cmd: str) -> str:
    """Send a command to a named pane."""
    target = _pane_target(name)
    if not target:
        return f"ERROR: Pane '{name}' not found"
    # Write cmd to temp file, load into tmux buffer, paste into pane
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cmd', delete=False) as f:
        f.write(cmd)
        tmpfile = f.name
    subprocess.run(
        ["tmux", "load-buffer", "-b", "sa_cmd", tmpfile],
        check=False,
    )
    os.unlink(tmpfile)
    subprocess.run(
        ["tmux", "paste-buffer", "-b", "sa_cmd", "-t", target, "-d"],
        check=False,
    )
    transport.send_keys(target, "Enter")
    return f"Sent to '{name}': {cmd}"


@mcp.tool()
def pane_output(name: str, lines: int = 50) -> str:
    """Capture recent output from a named pane."""
    target = _pane_target(name)
    if not target:
        return f"ERROR: Pane '{name}' not found"
    return transport.capture(target, lines)


@mcp.tool()
def pane_busy(name: str) -> bool:
    """Check if a named pane has a running process."""
    target = _pane_target(name)
    if not target:
        return False
    return transport.is_busy(target)


@mcp.tool()
def pane_kill(name: str) -> str:
    """Send Ctrl+C to a named pane."""
    target = _pane_target(name)
    if not target:
        return f"ERROR: Pane '{name}' not found"
    transport.send_keys(target, "C-c")
    return f"Sent Ctrl+C to '{name}'"


@mcp.tool()
def pane_close(name: str) -> str:
    """Close a named pane."""
    target = _pane_target(name)
    if not target:
        return f"Pane '{name}' not found (already closed?)"
    subprocess.run(
        ["tmux", "kill-pane", "-t", target],
        check=False,
    )
    _pane_registry.pop(name, None)
    return f"Closed pane '{name}'"


@mcp.tool()
def pane_focus(name: str) -> str:
    """Switch tmux focus to a named pane."""
    target = _pane_target(name)
    if not target:
        return f"ERROR: Pane '{name}' not found"
    subprocess.run(
        ["tmux", "select-pane", "-t", target],
        check=False,
    )
    return f"Focused on pane '{name}'"


@mcp.tool()
def pane_list() -> str:
    """List all named panes and their status."""
    if not _pane_registry:
        return "No named panes"
    lines = []
    for name, pane_id in list(_pane_registry.items()):
        target = _pane_target(name)
        if target:
            busy = transport.is_busy(target)
            status = "busy" if busy else "idle"
            lines.append(f"  {name}: {pane_id} [{status}]")
        else:
            lines.append(f"  {name}: (dead)")
    return "\n".join(lines)


# ──────────────────────────────────────────────
# Browser (w3m)
# ──────────────────────────────────────────────

BROWSE_WINDOW = "browse"


def _browse_pane() -> str:
    """Return the tmux target for the browser window."""
    return f"{transport.session_name()}:{BROWSE_WINDOW}"


def _is_w3m_running() -> bool:
    """Check if w3m is running in the browser window."""
    target = _browse_pane()
    try:
        r = subprocess.run(
            ["tmux", "display-message", "-t", target, "-p",
             "#{pane_current_command}"],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip() == "w3m"
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return False


def _browse_window_exists() -> bool:
    """Check if the browser window exists."""
    r = subprocess.run(
        ["tmux", "list-windows", "-t", transport.session_name(),
         "-F", "#{window_name}"],
        capture_output=True, text=True, timeout=5,
    )
    return BROWSE_WINDOW in r.stdout.splitlines()


def _ensure_browse_window():
    """Create the browser window if it doesn't exist."""
    if not _browse_window_exists():
        transport.create_window(BROWSE_WINDOW)
        time.sleep(0.3)


@mcp.tool()
def browse_open(url: str) -> str:
    """Open a URL in the browser (w3m in a dedicated tmux window).
    The page is visible in real-time in the 'browse' tmux window.
    Use browse_text() to read the content."""
    _ensure_browse_window()
    _focus_window(BROWSE_WINDOW)
    target = _browse_pane()
    if _is_w3m_running():
        # w3m is already running — open URL with U key
        transport.send_keys(target, "U")
        time.sleep(0.3)
        # Clear the URL line and type new URL
        transport.send_keys(target, "C-u")
        time.sleep(0.1)
        transport.send_literal(target, url)
        transport.send_keys(target, "Enter")
    else:
        transport.send_to_window(BROWSE_WINDOW, f"w3m {shlex.quote(url)}")
    time.sleep(2)
    return f"Opened {url} in browser"


@mcp.tool()
def browse_text(lines: int = 80) -> str:
    """Capture the currently visible browser content from the tmux pane.
    Returns what's on screen right now (text rendering of the page)."""
    if not _browse_window_exists():
        return "ERROR: Browser not open. Call browse_open(url) first."
    return transport.capture_window(BROWSE_WINDOW, lines)


@mcp.tool()
def browse_dump(url: str) -> str:
    """Fetch a URL and return its full text content using w3m -dump.
    Non-interactive — does NOT open in the browser window.
    Good for extracting full page text quickly."""
    r = subprocess.run(
        ["w3m", "-dump", "-cols", "120", url],
        capture_output=True, text=True, timeout=30,
    )
    if r.returncode != 0:
        return f"ERROR: w3m -dump failed: {r.stderr}"
    return r.stdout


@mcp.tool()
def browse_scroll(direction: str = "down", pages: int = 1) -> str:
    """Scroll the browser page.
    Args:
        direction: 'down' or 'up'
        pages: number of pages to scroll (default 1)
    """
    if not _browse_window_exists() or not _is_w3m_running():
        return "ERROR: Browser not open."
    target = _browse_pane()
    key = "Space" if direction == "down" else "b"
    for _ in range(pages):
        transport.send_keys(target, key)
        time.sleep(0.3)
    return f"Scrolled {direction} {pages} page(s)"


@mcp.tool()
def browse_follow(n: int = 1) -> str:
    """Move to the nth link on the page and follow it.
    Args:
        n: press Tab n times from current position to reach the link, then Enter
    """
    if not _browse_window_exists() or not _is_w3m_running():
        return "ERROR: Browser not open."
    target = _browse_pane()
    for _ in range(n):
        transport.send_keys(target, "Tab")
        time.sleep(0.15)
    transport.send_keys(target, "Enter")
    time.sleep(1.5)
    return f"Followed link (Tab x{n} + Enter)"


@mcp.tool()
def browse_back() -> str:
    """Go back to the previous page in the browser."""
    if not _browse_window_exists() or not _is_w3m_running():
        return "ERROR: Browser not open."
    transport.send_keys(_browse_pane(), "B")
    time.sleep(1)
    return "Went back"


@mcp.tool()
def browse_search(query: str) -> str:
    """Search for text on the current page.
    Use browse_search_next() to jump to the next match."""
    if not _browse_window_exists() or not _is_w3m_running():
        return "ERROR: Browser not open."
    target = _browse_pane()
    transport.send_keys(target, "/")
    time.sleep(0.2)
    transport.send_literal(target, query)
    transport.send_keys(target, "Enter")
    time.sleep(0.3)
    return f"Searched for '{query}'"


@mcp.tool()
def browse_search_next() -> str:
    """Jump to the next search match on the page."""
    if not _browse_window_exists() or not _is_w3m_running():
        return "ERROR: Browser not open."
    transport.send_keys(_browse_pane(), "n")
    time.sleep(0.2)
    return "Next match"


@mcp.tool()
def browse_url() -> str:
    """Get the current URL from the browser.
    Sends 'c' to w3m which shows current URL, then captures it."""
    if not _browse_window_exists() or not _is_w3m_running():
        return "ERROR: Browser not open."
    target = _browse_pane()
    transport.send_keys(target, "c")
    time.sleep(0.3)
    output = transport.capture_window(BROWSE_WINDOW, 3)
    # URL is shown at the bottom of the screen
    transport.send_keys(target, "q")  # dismiss URL display
    time.sleep(0.1)
    return output


@mcp.tool()
def browse_close() -> str:
    """Close the browser and its tmux window."""
    if not _browse_window_exists():
        return "Browser not open"
    target = _browse_pane()
    if _is_w3m_running():
        transport.send_keys(target, "Q")  # quit w3m without confirm
        time.sleep(0.3)
    transport.close_window(BROWSE_WINDOW)
    _focus_window("main")
    return "Browser closed"


# ──────────────────────────────────────────────
# Layout Presets
# ──────────────────────────────────────────────


@mcp.tool()
def layout(preset: str = "dev") -> str:
    """Apply a tmux pane layout preset.
    Presets:
        dev:   main (60%) | terminal (40%)
        review: main (60%) | diff top + log bottom (40%)
        multi: main (50%) | agent-1 top + agent-2 bottom (50%)
        reset: close all extra panes, back to single main
    """
    # Clean up: close ALL panes except pane index 0 in main window
    session = transport.session_name()
    r = subprocess.run(
        ["tmux", "list-panes", "-t", f"{session}:main",
         "-F", "#{pane_id} #{pane_index}"],
        capture_output=True, text=True, timeout=5,
    )
    if r.returncode == 0:
        for line in r.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1] != "0":
                subprocess.run(["tmux", "kill-pane", "-t", parts[0]], check=False)
    _pane_registry.clear()

    _focus_window("main")

    if preset == "reset":
        return "Layout reset to single main pane"

    if preset == "dev":
        pane_split("terminal", direction="horizontal", size=40)
        return "Layout: dev (main | terminal)"

    if preset == "review":
        pane_split("diff", direction="horizontal", size=40)
        pane_split("log", direction="vertical", size=50)
        return "Layout: review (main | diff + log)"

    if preset == "multi":
        pane_split("agent-1", direction="horizontal", size=50)
        pane_split("agent-2", direction="vertical", size=50)
        return "Layout: multi (main | agent-1 + agent-2)"

    return f"ERROR: Unknown preset '{preset}'. Use: dev, review, multi, reset"


# ──────────────────────────────────────────────
# Operation Log Access
# ──────────────────────────────────────────────


@mcp.tool()
def log_path() -> str:
    """Get the path to the current session's operation log file."""
    return op_logger.log_path


@mcp.tool()
def log_tail(n: int = 20) -> str:
    """Show the last n entries from the operation log."""
    try:
        with open(op_logger.log_path, "r") as f:
            lines = f.readlines()
        return "".join(lines[-n:])
    except FileNotFoundError:
        return "No log entries yet"


# ──────────────────────────────────────────────
# tmux Primitives (raw access)
# ──────────────────────────────────────────────


def _resolve_target(target: str) -> str:
    """Resolve a target: 'main' -> main pane, named pane -> pane_id, or raw tmux target."""
    if target == "main":
        return transport.main_pane()
    pane_id = _pane_registry.get(target)
    if pane_id:
        return pane_id
    return f"{transport.session_name()}:{target}"


@mcp.tool()
def send_keys(target: str, keys: str) -> str:
    """Send raw tmux keys to any pane.
    Args:
        target: 'main', a named pane, or a raw tmux target (e.g. 'shellagent:main.1')
        keys: tmux key string (e.g. 'C-c', 'Escape', 'Enter', 'C-l', or literal text)
    """
    t = _resolve_target(target)
    transport.send_keys(t, keys)
    return f"Sent keys '{keys}' to {target}"


@mcp.tool()
def capture(target: str = "main", lines: int = 50) -> str:
    """Capture text output from any pane.
    Args:
        target: 'main', a named pane, or raw tmux target
        lines: number of lines to capture from bottom (default 50)
    """
    t = _resolve_target(target)
    return transport.capture(t, lines)


@mcp.tool()
def scrollback(target: str = "main", lines: int = 2000) -> str:
    """Capture full scrollback buffer from any pane (not just visible area).
    Args:
        target: 'main', a named pane, or raw tmux target
        lines: max lines to capture (default 2000)
    """
    t = _resolve_target(target)
    r = subprocess.run(
        ["tmux", "capture-pane", "-t", t, "-p", "-S", f"-{lines}", "-J"],
        capture_output=True, text=True, timeout=10,
    )
    return r.stdout


@mcp.tool()
def pane_zoom(target: str = "main") -> str:
    """Toggle zoom (fullscreen) on a pane.
    Args:
        target: 'main', a named pane, or raw tmux target
    """
    t = _resolve_target(target)
    subprocess.run(["tmux", "resize-pane", "-t", t, "-Z"], check=False)
    return f"Toggled zoom on {target}"


@mcp.tool()
def pane_resize(name: str, direction: str, amount: int = 10) -> str:
    """Resize a named pane.
    Args:
        name: pane name from pane_split
        direction: 'left', 'right', 'up', 'down'
        amount: number of cells to resize (default 10)
    """
    target = _pane_target(name)
    if not target:
        return f"ERROR: Pane '{name}' not found"
    flag = {"left": "-L", "right": "-R", "up": "-U", "down": "-D"}.get(direction)
    if not flag:
        return f"ERROR: direction must be left/right/up/down"
    subprocess.run(
        ["tmux", "resize-pane", "-t", target, flag, str(amount)],
        check=False,
    )
    return f"Resized '{name}' {direction} by {amount}"


@mcp.tool()
def pane_swap(name1: str, name2: str) -> str:
    """Swap the positions of two named panes.
    Args:
        name1: first pane name
        name2: second pane name
    """
    t1 = _pane_target(name1)
    t2 = _pane_target(name2)
    if not t1:
        return f"ERROR: Pane '{name1}' not found"
    if not t2:
        return f"ERROR: Pane '{name2}' not found"
    subprocess.run(
        ["tmux", "swap-pane", "-s", t1, "-t", t2],
        check=False,
    )
    return f"Swapped '{name1}' and '{name2}'"


@mcp.tool()
def wait_for_idle(target: str = "main", timeout: int = 30) -> str:
    """Wait until a pane becomes idle (shell prompt).
    Args:
        target: 'main', a named pane, or raw tmux target
        timeout: max seconds to wait (default 30)
    Returns: 'idle' or 'timeout'
    """
    t = _resolve_target(target)
    for _ in range(timeout * 5):
        if not transport.is_busy(t):
            return "idle"
        time.sleep(0.2)
    return "timeout"


@mcp.tool()
def pipe_log(name: str, log_file: str) -> str:
    """Start piping a named pane's output to a file (real-time logging).
    Call pipe_log_stop() to stop.
    Args:
        name: pane name
        log_file: absolute path to write output to
    """
    target = _pane_target(name)
    if not target:
        return f"ERROR: Pane '{name}' not found"
    full = os.path.expanduser(log_file)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    subprocess.run(
        ["tmux", "pipe-pane", "-t", target, f"cat >> {full}"],
        check=False,
    )
    return f"Piping '{name}' output to {full}"


@mcp.tool()
def pipe_log_stop(name: str) -> str:
    """Stop piping a pane's output to file."""
    target = _pane_target(name)
    if not target:
        return f"ERROR: Pane '{name}' not found"
    subprocess.run(
        ["tmux", "pipe-pane", "-t", target],  # empty command = stop
        check=False,
    )
    return f"Stopped piping '{name}'"


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
