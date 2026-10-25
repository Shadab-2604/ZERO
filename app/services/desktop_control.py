"""
Zero AI Safe Windows Desktop Control & System Awareness Service.

Strict Security & Permission Policy:
- ALLOWED:
  - Enumerate visible application windows and titles.
  - Enumerate running user processes and resource metadata.
  - Discover installed applications from Start Menu and registered App Paths.
  - Read-only OS, CPU, Memory, Disk, and Network telemetry.
  - Launch verified application executables (no arbitrary command strings or shell scripts).
  - Bring to foreground, minimize, restore, and maximize windows.
  - Gracefully request window closure via WM_CLOSE (detect unsaved prompts without auto-dismissing).
- PROHIBITED:
  - Arbitrary filesystem writing, deletion, or modification.
  - Windows registry modifications.
  - System or firewall setting alterations.
  - Arbitrary CMD/PowerShell/bash command execution.
  - Force killing processes (SIGKILL / taskkill /F).
  - Reading credential databases, private keys, or .env files.
  - Requesting administrator elevation.
"""

import ctypes
import logging
import os
import platform
import re
import subprocess
import time
import winreg
from typing import Any

import psutil

logger = logging.getLogger(__name__)

# Try importing pywin32 modules
try:
    import win32api
    import win32con
    import win32gui
    import win32process
    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False
    logger.warning("pywin32 not fully available; falling back to ctypes for desktop automation.")


class DesktopControlService:
    """Windows desktop automation and system awareness engine."""

    def __init__(self):
        self._user32 = ctypes.windll.user32
        self._known_apps_cache: dict[str, str] = {}
        self._refresh_known_applications()

    def _refresh_known_applications(self) -> None:
        """Scan system for registered applications and Start Menu shortcuts."""
        apps: dict[str, str] = {}

        # 1. Standard Windows Utilities
        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        system32 = os.path.join(system_root, "System32")
        builtins = {
            "notepad": os.path.join(system_root, "notepad.exe"),
            "calculator": os.path.join(system32, "calc.exe"),
            "calc": os.path.join(system32, "calc.exe"),
            "mspaint": os.path.join(system32, "mspaint.exe"),
            "paint": os.path.join(system32, "mspaint.exe"),
            "explorer": os.path.join(system_root, "explorer.exe"),
            "cmd": os.path.join(system32, "cmd.exe"),
            "powershell": os.path.join(system32, "WindowsPowerShell", "v1.0", "powershell.exe"),
            "taskmgr": os.path.join(system32, "taskmgr.exe"),
            "task manager": os.path.join(system32, "taskmgr.exe"),
        }
        for name, path in builtins.items():
            if os.path.exists(path):
                apps[name] = path

        # 2. Windows Registry App Paths
        reg_keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
        ]
        for root, subkey in reg_keys:
            try:
                with winreg.OpenKey(root, subkey) as key:
                    count = winreg.QueryInfoKey(key)[0]
                    for i in range(count):
                        try:
                            app_sub = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, app_sub) as app_key:
                                exe_path, _ = winreg.QueryValueEx(app_key, "")
                                exe_path = exe_path.strip('"')
                                if os.path.exists(exe_path) and exe_path.lower().endswith(".exe"):
                                    base_name = os.path.splitext(app_sub)[0].lower()
                                    apps[base_name] = exe_path
                                    # Common mappings
                                    if "chrome" in base_name:
                                        apps["chrome"] = exe_path
                                        apps["google chrome"] = exe_path
                                    elif "code" in base_name:
                                        apps["vs code"] = exe_path
                                        apps["vscode"] = exe_path
                                        apps["visual studio code"] = exe_path
                                    elif "msedge" in base_name or "edge" in base_name:
                                        apps["edge"] = exe_path
                                        apps["microsoft edge"] = exe_path
                                    elif "firefox" in base_name:
                                        apps["firefox"] = exe_path
                                    elif "brave" in base_name:
                                        apps["brave"] = exe_path
                        except (OSError, WindowsError):
                            continue
            except (OSError, WindowsError):
                pass

        # 3. Start Menu Shortcuts (.lnk targets)
        start_menu_dirs = [
            os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), r"Microsoft\Windows\Start Menu\Programs"),
            os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
        ]
        for sm_dir in start_menu_dirs:
            if not os.path.exists(sm_dir):
                continue
            for root, _, files in os.walk(sm_dir):
                for f in files:
                    if f.lower().endswith(".lnk"):
                        app_name = os.path.splitext(f)[0].lower()
                        lnk_path = os.path.join(root, f)
                        target = self._resolve_shortcut(lnk_path)
                        if target and os.path.exists(target) and target.lower().endswith(".exe"):
                            apps[app_name] = target
                            if "visual studio code" in app_name or "vs code" in app_name:
                                apps["vs code"] = target
                                apps["vscode"] = target
                                apps["code"] = target
                            elif "google chrome" in app_name:
                                apps["chrome"] = target
                                apps["google chrome"] = target

        self._known_apps_cache = apps

    @staticmethod
    def _resolve_shortcut(lnk_path: str) -> str | None:
        """Resolve a Windows .lnk shortcut target path without shell execution."""
        try:
            import pythoncom
            from win32com.client import Dispatch
            pythoncom.CoInitialize()
            shell = Dispatch("WScript.Shell")
            shortcut = shell.CreateShortcut(lnk_path)
            target = shortcut.TargetPath
            pythoncom.CoUninitialize()
            return target if target and os.path.exists(target) else None
        except Exception:
            return None

    def _ensure_interactive_desktop(self) -> int | None:
        """Ensure current thread is attached to the interactive 'Default' desktop in WinSta0."""
        try:
            h_def = self._user32.OpenDesktopW("Default", 0, False, 0x01FF)
            if h_def:
                self._user32.SetThreadDesktop(h_def)
                return h_def
        except Exception as e:
            logger.debug("Could not attach to Default desktop: %s", e)
        return None

    # =========================================================================
    # Window Enumeration & Inspection
    # =========================================================================

    def list_windows(self) -> list[dict[str, Any]]:
        """
        Enumerate all visible top-level application windows.
        Returns: list of dicts with hwnd, title, pid, process_name, is_minimized, is_maximized.
        """
        windows: list[dict[str, Any]] = []

        if not PYWIN32_AVAILABLE:
            return windows

        h_def = self._ensure_interactive_desktop()
        seen_hwnds = set()

        def _enum_handler(hwnd: int, _lparam: Any):
            try:
                if hwnd in seen_hwnds:
                    return True
                seen_hwnds.add(hwnd)

                if not win32gui.IsWindowVisible(hwnd):
                    return True
                title = win32gui.GetWindowText(hwnd).strip()
                if not title:
                    return True

                # Exclude known Windows shell utility windows
                if title in ("Program Manager", "Settings", "Windows Input Experience", "Task Switching"):
                    return True

                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                proc_name = ""
                try:
                    proc = psutil.Process(pid)
                    proc_name = proc.name()
                except Exception:
                    proc_name = "unknown"

                is_minimized = bool(self._user32.IsIconic(hwnd))
                is_maximized = bool(self._user32.IsZoomed(hwnd))

                windows.append({
                    "hwnd": hwnd,
                    "title": title,
                    "pid": pid,
                    "process_name": proc_name,
                    "is_minimized": is_minimized,
                    "is_maximized": is_maximized,
                })
            except Exception as e:
                logger.debug("Error inspecting hwnd %d: %s", hwnd, e)

            return True

        if h_def:
            try:
                win32gui.EnumDesktopWindows(h_def, _enum_handler, None)
            except Exception as e:
                logger.debug("EnumDesktopWindows notice: %s", e)
        try:
            win32gui.EnumWindows(_enum_handler, None)
        except Exception as e:
            logger.debug("EnumWindows notice: %s", e)

        return windows

    def list_running_applications(self) -> list[dict[str, Any]]:
        """
        List distinct active desktop applications with visible windows and resource usage.
        """
        wins = self.list_windows()
        seen_pids = set()
        apps: list[dict[str, Any]] = []

        for w in wins:
            pid = w["pid"]
            if pid in seen_pids:
                continue
            seen_pids.add(pid)
            try:
                proc = psutil.Process(pid)
                cpu = proc.cpu_percent(interval=0.0)
                mem_mb = round(proc.memory_info().rss / (1024 * 1024), 1)
                apps.append({
                    "name": proc.name(),
                    "title": w["title"],
                    "pid": pid,
                    "cpu_percent": cpu,
                    "memory_mb": mem_mb,
                    "is_minimized": w["is_minimized"],
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                apps.append({
                    "name": w["process_name"],
                    "title": w["title"],
                    "pid": pid,
                    "cpu_percent": 0.0,
                    "memory_mb": 0.0,
                    "is_minimized": w["is_minimized"],
                })

        return apps

    # =========================================================================
    # Window Matching
    # =========================================================================

    def find_window(self, identifier: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        """
        Find a window by natural-language title or process name substring.
        Returns: (best_match_dict_or_None, all_candidate_matches)
        """
        if not identifier or not identifier.strip():
            return None, []

        clean_id = identifier.strip().lower()
        windows = self.list_windows()

        # Alias expansion
        target_tokens = clean_id.split()
        if "chrome" in clean_id:
            target_tokens.append("google chrome")
        if "vs code" in clean_id or "vscode" in clean_id or clean_id == "code":
            target_tokens.extend(["visual studio code", "code.exe"])
        if "notepad" in clean_id:
            target_tokens.extend(["notepad", "notepad.exe"])
        if "calculator" in clean_id or "calc" in clean_id:
            target_tokens.extend(["calculator", "calc"])

        matches: list[dict[str, Any]] = []
        for w in windows:
            title_lower = w["title"].lower()
            proc_lower = w["process_name"].lower()
            if any(t in title_lower or t in proc_lower for t in target_tokens):
                matches.append(w)

        if not matches:
            return None, []

        # If exactly one match, return it
        if len(matches) == 1:
            return matches[0], matches

        # If multiple, prioritize visible non-minimized or exact title match
        for m in matches:
            if clean_id in m["title"].lower():
                return m, matches

        return matches[0], matches

    # =========================================================================
    # Window Actions (Focus, Minimize, Restore, Maximize, Close)
    # =========================================================================

    def focus_window(self, window_identifier: str) -> dict[str, Any]:
        """Restore (if minimized) and bring target window to foreground."""
        target, candidates = self.find_window(window_identifier)
        if not target:
            return {
                "action": "focus_window",
                "target": window_identifier,
                "success": False,
                "verified": False,
                "message": f"Could not find an open window matching '{window_identifier}'.",
            }

        hwnd = target["hwnd"]
        try:
            if target["is_minimized"]:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.15)
            fg = win32gui.GetForegroundWindow()
            verified = (fg == hwnd)
            return {
                "action": "focus_window",
                "target": target["title"],
                "success": True,
                "verified": verified,
                "message": f"Switched to '{target['title']}'.",
            }
        except Exception as e:
            return {
                "action": "focus_window",
                "target": target["title"],
                "success": False,
                "verified": False,
                "message": f"Failed to focus window '{target['title']}': {str(e)}",
            }

    def minimize_window(self, window_identifier: str) -> dict[str, Any]:
        """Minimize the identified window and verify iconic state."""
        target, candidates = self.find_window(window_identifier)
        if not target:
            return {
                "action": "minimize_window",
                "target": window_identifier,
                "success": False,
                "verified": False,
                "message": f"Could not find an open window matching '{window_identifier}'.",
            }

        hwnd = target["hwnd"]
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            time.sleep(0.15)
            verified = bool(self._user32.IsIconic(hwnd))
            return {
                "action": "minimize_window",
                "target": target["title"],
                "success": True,
                "verified": verified,
                "message": f"Minimized '{target['title']}'." if verified else f"Attempted to minimize '{target['title']}'.",
            }
        except Exception as e:
            return {
                "action": "minimize_window",
                "target": target["title"],
                "success": False,
                "verified": False,
                "message": f"Error minimizing '{target['title']}': {str(e)}",
            }

    def restore_window(self, window_identifier: str) -> dict[str, Any]:
        """Restore a minimized window to normal state and verify."""
        target, candidates = self.find_window(window_identifier)
        if not target:
            return {
                "action": "restore_window",
                "target": window_identifier,
                "success": False,
                "verified": False,
                "message": f"Could not find an open window matching '{window_identifier}'.",
            }

        hwnd = target["hwnd"]
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.15)
            try:
                win32gui.SetForegroundWindow(hwnd)
            except Exception as e_fg:
                logger.debug("SetForegroundWindow restricted by Windows foreground policy: %s", e_fg)

            verified = not bool(self._user32.IsIconic(hwnd))
            return {
                "action": "restore_window",
                "target": target["title"],
                "success": True,
                "verified": verified,
                "message": f"Restored '{target['title']}'." if verified else f"Attempted to restore '{target['title']}'.",
            }
        except Exception as e:
            return {
                "action": "restore_window",
                "target": target["title"],
                "success": False,
                "verified": False,
                "message": f"Error restoring '{target['title']}': {str(e)}",
            }

    def maximize_window(self, window_identifier: str) -> dict[str, Any]:
        """Maximize the selected window and verify zoomed state."""
        target, candidates = self.find_window(window_identifier)
        if not target:
            return {
                "action": "maximize_window",
                "target": window_identifier,
                "success": False,
                "verified": False,
                "message": f"Could not find an open window matching '{window_identifier}'.",
            }

        hwnd = target["hwnd"]
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            time.sleep(0.15)
            verified = bool(self._user32.IsZoomed(hwnd))
            return {
                "action": "maximize_window",
                "target": target["title"],
                "success": True,
                "verified": verified,
                "message": f"Maximized '{target['title']}'." if verified else f"Attempted to maximize '{target['title']}'.",
            }
        except Exception as e:
            return {
                "action": "maximize_window",
                "target": target["title"],
                "success": False,
                "verified": False,
                "message": f"Error maximizing '{target['title']}': {str(e)}",
            }

    def request_close_window(self, window_identifier: str) -> dict[str, Any]:
        """
        Request graceful window closure using WM_CLOSE.
        Checks if the window closed or if an unsaved-changes prompt was presented.
        Never forcibly kills the process. Never auto-clicks Save or Discard.
        """
        target, candidates = self.find_window(window_identifier)
        if not target:
            return {
                "action": "request_close_window",
                "target": window_identifier,
                "success": False,
                "verified": False,
                "message": f"Could not find an open window matching '{window_identifier}'.",
            }

        hwnd = target["hwnd"]
        title = target["title"]
        pid = target["pid"]

        try:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            time.sleep(0.35)

            # Check if window is still alive
            is_alive = bool(win32gui.IsWindow(hwnd))
            if not is_alive:
                return {
                    "action": "request_close_window",
                    "target": title,
                    "success": True,
                    "verified": True,
                    "message": f"Successfully closed '{title}'.",
                }

            # Check if an unsaved prompt / modal child appeared
            child_dialogs: list[str] = []
            def _find_children(child_hwnd: int, _):
                if win32gui.IsWindowVisible(child_hwnd):
                    child_title = win32gui.GetWindowText(child_hwnd).strip()
                    if child_title:
                        child_dialogs.append(child_title)
                return True

            try:
                win32gui.EnumChildWindows(hwnd, _find_children, None)
            except Exception:
                pass

            if child_dialogs or is_alive:
                return {
                    "action": "request_close_window",
                    "target": title,
                    "success": True,
                    "verified": True,
                    "prompt_detected": True,
                    "message": (
                        f"Close request sent to '{title}'. The application has unsaved changes or a confirmation prompt. "
                        "Zero will not discard or save your work automatically; please confirm manually."
                    ),
                }

            return {
                "action": "request_close_window",
                "target": title,
                "success": True,
                "verified": True,
                "message": f"Closed window '{title}'.",
            }
        except Exception as e:
            return {
                "action": "request_close_window",
                "target": title,
                "success": False,
                "verified": False,
                "message": f"Error requesting close for '{title}': {str(e)}",
            }

    # =========================================================================
    # Application Discovery & Safe Launching
    # =========================================================================

    def find_application(self, app_name: str) -> str | None:
        """Find the executable path of an installed or registered application."""
        clean_name = re.sub(r"[^\w\s\.\-]", "", app_name).strip().lower()
        if not clean_name:
            return None
        self._refresh_known_applications()
        if clean_name in self._known_apps_cache:
            return self._known_apps_cache[clean_name]
        for name, path in self._known_apps_cache.items():
            if clean_name in name or name in clean_name:
                return path
        return None

    def open_application(self, app_name: str) -> dict[str, Any]:
        """
        Open or switch to an installed application by name.
        If already running with a visible window, brings it to foreground instead of launching duplicates.
        Only launches validated, allowlisted executables.
        """
        clean_name = re.sub(r"[^\w\s\.\-]", "", app_name).strip().lower()
        if not clean_name:
            return {
                "action": "open_application",
                "target": app_name,
                "success": False,
                "verified": False,
                "message": "Invalid application name provided.",
            }

        # 1. Check if application is already open
        running_target, _ = self.find_window(clean_name)
        if running_target:
            focus_res = self.focus_window(running_target["title"])
            return {
                "action": "open_application",
                "target": running_target["title"],
                "success": True,
                "verified": True,
                "already_running": True,
                "message": f"'{running_target['title']}' is already running. Brought to foreground.",
            }

        # 2. Lookup executable path
        exe_path = self.find_application(clean_name)

        if not exe_path or not os.path.exists(exe_path):
            return {
                "action": "open_application",
                "target": app_name,
                "success": False,
                "verified": False,
                "message": f"Application '{app_name}' could not be found among installed or registered applications.",
            }

        # 3. Safe launch via validated path without shell
        try:
            logger.info("Safely launching validated application executable: %s", exe_path)
            subprocess.Popen([exe_path], close_fds=True)
            time.sleep(0.6)

            # Check if process launched
            base_exe = os.path.basename(exe_path).lower()
            launched = False
            for p in psutil.process_iter(["name"]):
                try:
                    if p.info["name"] and p.info["name"].lower() == base_exe:
                        launched = True
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return {
                "action": "open_application",
                "target": app_name,
                "executable": exe_path,
                "success": True,
                "verified": launched,
                "message": f"Opened {app_name} successfully." if launched else f"Started {app_name}.",
            }
        except Exception as e:
            return {
                "action": "open_application",
                "target": app_name,
                "success": False,
                "verified": False,
                "message": f"Failed to launch '{app_name}': {str(e)}",
            }

    # =========================================================================
    # System Awareness Telemetry
    # =========================================================================

    def get_system_status(self) -> dict[str, Any]:
        """
        Read-only Windows system overview:
        - Operating System and Version
        - CPU Model & Current Utilization
        - RAM Total & Available
        - Disk Capacity & Free Space
        - Network Adapters & IP Configuration
        - Running Application Count
        - Ollama Local Service State
        """
        try:
            # OS Info
            os_info = f"Windows {platform.release()} (Build {platform.version()})"

            # CPU
            cpu_pct = psutil.cpu_percent(interval=0.15)
            cpu_count = psutil.cpu_count(logical=True)
            cpu_model = platform.processor() or "Intel/AMD x64 Processor"

            # RAM
            mem = psutil.virtual_memory()
            ram_total_gb = round(mem.total / (1024**3), 1)
            ram_avail_gb = round(mem.available / (1024**3), 1)
            ram_pct = mem.percent

            # Disk
            disk = psutil.disk_usage("C:\\")
            disk_total_gb = round(disk.total / (1024**3), 1)
            disk_free_gb = round(disk.free / (1024**3), 1)
            disk_pct = disk.percent

            # Network
            adapters: list[dict[str, str]] = []
            for name, snics in psutil.net_if_addrs().items():
                for snic in snics:
                    if snic.family.name == "AF_INET" and not snic.address.startswith("127."):
                        adapters.append({"adapter": name, "ip": snic.address})

            # Running Apps
            running_apps = self.list_running_applications()

            # Ollama Check
            import httpx
            from app.config.settings import get_settings
            settings = get_settings()
            base_url = settings.ai_api_base.replace("/v1", "")
            ollama_status = "OFFLINE"
            ollama_models = []
            try:
                with httpx.Client(timeout=2.0) as client:
                    r = client.get(f"{base_url}/api/tags")
                    if r.status_code == 200:
                        ollama_status = "ONLINE"
                        ollama_models = [m.get("name") for m in r.json().get("models", [])]
            except Exception:
                ollama_status = "OFFLINE"

            summary = (
                f"{os_info}. CPU usage is at {cpu_pct}%, RAM is at {ram_pct}% ({ram_avail_gb} GB available), "
                f"and {disk_free_gb} GB disk space is free on drive C. {len(running_apps)} applications are active."
            )

            detailed_lines = [
                "### Windows System Telemetry & Awareness\n",
                f"- **Operating System:** `{os_info}` ({platform.machine()})",
                f"- **CPU:** `{cpu_model}` — `{cpu_pct}%` utilization (`{cpu_count}` logical cores)",
                f"- **RAM:** `{ram_avail_gb} GB available / {ram_total_gb} GB total` (`{ram_pct}%` used)",
                f"- **Drive C:** `{disk_free_gb} GB free / {disk_total_gb} GB total` (`{disk_pct}%` used)",
                f"- **Active Network Adapters:**",
            ]
            for a in adapters:
                detailed_lines.append(f"  - `{a['adapter']}`: `{a['ip']}`")
            if not adapters:
                detailed_lines.append("  - `No active IPv4 external adapter detected`")

            detailed_lines.append(f"- **Local AI (Ollama):** `{ollama_status}` (`{len(ollama_models)}` models installed)")
            detailed_lines.append(f"- **Running Applications ({len(running_apps)}):**")
            for app in running_apps[:8]:
                detailed_lines.append(f"  - **{app['name']}** — *\"{app['title'][:40]}\"* (`{app['memory_mb']} MB`)")
            if len(running_apps) > 8:
                detailed_lines.append(f"  - *...and {len(running_apps) - 8} more applications*")

            detailed_text = "\n".join(detailed_lines)

            return {
                "success": True,
                "summary": summary,
                "detailed_text": detailed_text,
                "telemetry": {
                    "os": os_info,
                    "cpu_pct": cpu_pct,
                    "ram_pct": ram_pct,
                    "ram_avail_gb": ram_avail_gb,
                    "disk_free_gb": disk_free_gb,
                    "network_adapters": adapters,
                    "running_apps_count": len(running_apps),
                    "ollama_status": ollama_status,
                    "ollama_models": ollama_models,
                },
            }
        except Exception as e:
            logger.error("Error gathering system telemetry: %s", e)
            return {
                "success": False,
                "summary": "Could not retrieve system telemetry.",
                "detailed_text": f"**Telemetry Error:** {str(e)}",
                "telemetry": {},
            }


# Singleton service instance
_global_desktop_service: DesktopControlService | None = None


def get_desktop_service() -> DesktopControlService:
    global _global_desktop_service
    if _global_desktop_service is None:
        _global_desktop_service = DesktopControlService()
    return _global_desktop_service


class _DesktopControlProxy:
    """Proxy object providing attribute access to the singleton desktop service."""
    def __getattr__(self, name):
        return getattr(get_desktop_service(), name)


desktop_control = _DesktopControlProxy()

