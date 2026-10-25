"""
Safe allowlisted desktop window and application management tools for Zero AI.
Enforces strict parameter validation, verified execution results, and natural spoken summaries.
"""

import logging
from typing import Any
from app.services.desktop_control import get_desktop_service
from app.tools.registry import ActionRegistry, ToolResult

logger = logging.getLogger(__name__)


def open_application(app_name: str) -> ToolResult:
    """Open or focus an installed Windows application safely."""
    svc = get_desktop_service()
    res = svc.open_application(app_name)
    success = res.get("success", False)
    msg = res.get("message", "")
    target = res.get("target", app_name)

    if success:
        detailed = (
            f"### Application Action: Open\n\n"
            f"- **Target Application:** `{target}`\n"
            f"- **Execution Status:** `SUCCESS` (Verified: `{res.get('verified', False)}`)\n"
            f"- **Outcome:** {msg}\n"
        )
        return ToolResult(
            success=True,
            summary=msg,
            detailed_text=detailed,
            data=res,
        )
    else:
        detailed = (
            f"### Application Action: Open Failed\n\n"
            f"- **Target Application:** `{target}`\n"
            f"- **Status:** `NOT FOUND / FAILED`\n"
            f"- **Notice:** {msg}\n"
        )
        return ToolResult(
            success=False,
            summary=msg,
            detailed_text=detailed,
            error=msg,
            data=res,
        )


def minimize_window(identifier: str) -> ToolResult:
    """Minimize a specified open application window."""
    svc = get_desktop_service()
    res = svc.minimize_window(identifier)
    success = res.get("success", False)
    msg = res.get("message", "")
    target = res.get("target", identifier)

    detailed = (
        f"### Window Action: Minimize\n\n"
        f"- **Window Target:** `{target}`\n"
        f"- **State:** `{'MINIMIZED' if success else 'NOT MINIMIZED'}` (Verified: `{res.get('verified', False)}`)\n"
        f"- **Result:** {msg}\n"
    )
    return ToolResult(
        success=success,
        summary=msg,
        detailed_text=detailed,
        data=res,
        error=None if success else msg,
    )


def restore_window(identifier: str) -> ToolResult:
    """Restore a minimized window to normal foreground state."""
    svc = get_desktop_service()
    res = svc.restore_window(identifier)
    success = res.get("success", False)
    msg = res.get("message", "")
    target = res.get("target", identifier)

    detailed = (
        f"### Window Action: Restore\n\n"
        f"- **Window Target:** `{target}`\n"
        f"- **State:** `{'RESTORED' if success else 'FAILED'}` (Verified: `{res.get('verified', False)}`)\n"
        f"- **Result:** {msg}\n"
    )
    return ToolResult(
        success=success,
        summary=msg,
        detailed_text=detailed,
        data=res,
        error=None if success else msg,
    )


def maximize_window(identifier: str) -> ToolResult:
    """Maximize a specified open application window."""
    svc = get_desktop_service()
    res = svc.maximize_window(identifier)
    success = res.get("success", False)
    msg = res.get("message", "")
    target = res.get("target", identifier)

    detailed = (
        f"### Window Action: Maximize\n\n"
        f"- **Window Target:** `{target}`\n"
        f"- **State:** `{'MAXIMIZED' if success else 'FAILED'}` (Verified: `{res.get('verified', False)}`)\n"
        f"- **Result:** {msg}\n"
    )
    return ToolResult(
        success=success,
        summary=msg,
        detailed_text=detailed,
        data=res,
        error=None if success else msg,
    )


def focus_window(identifier: str) -> ToolResult:
    """Switch to and bring target window to the foreground."""
    svc = get_desktop_service()
    res = svc.focus_window(identifier)
    success = res.get("success", False)
    msg = res.get("message", "")
    target = res.get("target", identifier)

    detailed = (
        f"### Window Action: Switch Focus\n\n"
        f"- **Window Target:** `{target}`\n"
        f"- **State:** `{'FOREGROUND' if success else 'FAILED'}` (Verified: `{res.get('verified', False)}`)\n"
        f"- **Result:** {msg}\n"
    )
    return ToolResult(
        success=success,
        summary=msg,
        detailed_text=detailed,
        data=res,
        error=None if success else msg,
    )


def close_window(identifier: str) -> ToolResult:
    """Request graceful close for a specified window without force killing."""
    svc = get_desktop_service()
    res = svc.request_close_window(identifier)
    success = res.get("success", False)
    msg = res.get("message", "")
    target = res.get("target", identifier)

    detailed = (
        f"### Window Action: Graceful Close\n\n"
        f"- **Window Target:** `{target}`\n"
        f"- **Action:** `WM_CLOSE Sent` (Verified: `{res.get('verified', False)}`)\n"
        f"- **Result:** {msg}\n"
    )
    return ToolResult(
        success=success,
        summary=msg,
        detailed_text=detailed,
        data=res,
        error=None if success else msg,
    )


def list_open_windows() -> ToolResult:
    """List all currently open and visible application windows on Windows."""
    svc = get_desktop_service()
    wins = svc.list_windows()

    if not wins:
        summary = "There are currently no visible application windows detected."
        detailed = "### Active Windows\n\nNo visible application windows were found."
        return ToolResult(success=True, summary=summary, detailed_text=detailed, data={"windows": []})

    summary = f"There are currently {len(wins)} active application windows open."
    lines = [f"### Currently Open Windows ({len(wins)})\n"]
    for w in wins:
        state_tag = " [MINIMIZED]" if w["is_minimized"] else (" [MAXIMIZED]" if w["is_maximized"] else "")
        lines.append(f"- **{w['process_name']}** — *\"{w['title']}\"*{state_tag} (PID: `{w['pid']}`)")

    return ToolResult(
        success=True,
        summary=summary,
        detailed_text="\n".join(lines),
        data={"windows": wins},
    )


def list_running_applications() -> ToolResult:
    """List all distinct user-facing applications currently running."""
    svc = get_desktop_service()
    apps = svc.list_running_applications()

    if not apps:
        summary = "No user-facing applications are currently active."
        detailed = "### Running Applications\n\nNo user-facing applications detected."
        return ToolResult(success=True, summary=summary, detailed_text=detailed, data={"apps": []})

    summary = f"I detected {len(apps)} applications running with visible windows."
    lines = [f"### Active User Applications ({len(apps)})\n"]
    for a in apps:
        lines.append(f"- **{a['name']}** — *\"{a['title'][:45]}\"* (`{a['memory_mb']} MB RAM`)")

    return ToolResult(
        success=True,
        summary=summary,
        detailed_text="\n".join(lines),
        data={"apps": apps},
    )


def get_system_overview() -> ToolResult:
    """Read-only system awareness telemetry covering OS, CPU, RAM, Disk, Network, and Ollama."""
    svc = get_desktop_service()
    res = svc.get_system_status()
    return ToolResult(
        success=res.get("success", False),
        summary=res.get("summary", "System telemetry retrieved."),
        detailed_text=res.get("detailed_text", ""),
        data=res.get("telemetry", {}),
    )


def register_desktop_tools(registry: ActionRegistry) -> None:
    """Register all allowlisted desktop automation and window management tools."""
    registry.register(
        name="open_application",
        description="Open an installed Windows application by name, or bring it to foreground if already running.",
        handler=open_application,
        parameters={"app_name": {"type": "string", "description": "Application name to open (e.g. Chrome, Notepad, VS Code)"}},
    )
    registry.register(
        name="minimize_window",
        description="Minimize an open application window by name or title.",
        handler=minimize_window,
        parameters={"identifier": {"type": "string", "description": "Application or window title to minimize"}},
    )
    registry.register(
        name="restore_window",
        description="Restore a minimized application window and bring to foreground.",
        handler=restore_window,
        parameters={"identifier": {"type": "string", "description": "Application or window title to restore"}},
    )
    registry.register(
        name="maximize_window",
        description="Maximize an open application window.",
        handler=maximize_window,
        parameters={"identifier": {"type": "string", "description": "Application or window title to maximize"}},
    )
    registry.register(
        name="focus_window",
        description="Switch to and focus an application window.",
        handler=focus_window,
        parameters={"identifier": {"type": "string", "description": "Application or window title to switch to"}},
    )
    registry.register(
        name="close_window",
        description="Request graceful closure of an application window via WM_CLOSE.",
        handler=close_window,
        parameters={"identifier": {"type": "string", "description": "Application or window title to close"}},
    )
    registry.register(
        name="list_open_windows",
        description="Enumerate all visible top-level application windows.",
        handler=list_open_windows,
        parameters={},
    )
    registry.register(
        name="list_running_applications",
        description="List active user applications with titles and resource usage.",
        handler=list_running_applications,
        parameters={},
    )
    registry.register(
        name="get_system_overview",
        description="Get read-only Windows system telemetry (CPU, RAM, Disk, Network, Apps, Ollama).",
        handler=get_system_overview,
        parameters={},
    )
