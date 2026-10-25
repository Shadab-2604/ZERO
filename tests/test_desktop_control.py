"""
Mocked unit tests and validation tests for Windows Desktop Automation,
Application Discovery, Window Management, Strict Security Allowlist,
and Spoken Confirmations.
"""

from unittest.mock import MagicMock, patch
import pytest

from app.core.assistant import ZeroAssistant
from app.services.desktop_control import (
    DesktopControlService,
    get_desktop_service,
)
from app.tools.desktop_tools import (
    open_application,
    minimize_window,
    restore_window,
    maximize_window,
    focus_window,
    close_window,
    list_open_windows,
    list_running_applications,
    get_system_overview,
)
from app.tools.registry import ActionRegistry, get_action_registry


# =============================================================================
# 1. Application Discovery Tests
# =============================================================================
def test_application_discovery_known_apps():
    svc = DesktopControlService()

    # Test discovery of built-in and common targets
    notepad_target = svc.find_application("notepad")
    assert notepad_target is not None
    assert "notepad.exe" in notepad_target.lower()

    calc_target = svc.find_application("calculator")
    assert calc_target is not None
    assert "calc.exe" in calc_target.lower() or "calc" in calc_target.lower()

    cmd_target = svc.find_application("cmd")
    assert cmd_target is not None
    assert "cmd.exe" in cmd_target.lower()


# =============================================================================
# 2. Missing Applications (Truthful reporting, no hallucinations)
# =============================================================================
def test_missing_application_returns_truthful_failure():
    svc = DesktopControlService()

    # Query for nonexistent application
    target = svc.find_application("completely_nonexistent_software_xyz_9999")
    assert target is None

    result = svc.open_application("completely_nonexistent_software_xyz_9999")
    assert result["success"] is False
    assert result["verified"] is False
    assert "could not be found" in result["message"].lower()


# =============================================================================
# 3. Ambiguous Window Titles
# =============================================================================
def test_ambiguous_window_titles_handling():
    svc = DesktopControlService()

    # Mock list_windows returning multiple matching windows
    mock_windows = [
        {"hwnd": 1001, "title": "Document 1 - Notepad", "pid": 501, "process_name": "notepad.exe", "is_minimized": False, "is_maximized": False},
        {"hwnd": 1002, "title": "Document 2 - Notepad", "pid": 502, "process_name": "notepad.exe", "is_minimized": False, "is_maximized": False},
    ]

    with patch.object(svc, "list_windows", return_value=mock_windows):
        best_match, all_matches = svc.find_window("Notepad")
        assert len(all_matches) == 2
        assert all_matches[0]["hwnd"] == 1001
        assert all_matches[1]["hwnd"] == 1002


# =============================================================================
# 4. Minimization, Restoration, and Maximization Verification
# =============================================================================
def test_minimize_window_verified():
    svc = DesktopControlService()
    mock_win = {"hwnd": 1001, "title": "TestApp", "pid": 501, "process_name": "test.exe", "is_minimized": False, "is_maximized": False}

    with patch.object(svc, "find_window", return_value=(mock_win, [mock_win])), \
         patch("win32gui.ShowWindow") as mock_show, \
         patch.object(svc._user32, "IsIconic", return_value=1):

        res = svc.minimize_window("TestApp")
        assert res["success"] is True
        assert res["verified"] is True
        assert "minimized" in res["message"].lower()
        mock_show.assert_called_once()


def test_restore_window_verified():
    svc = DesktopControlService()
    mock_win = {"hwnd": 1001, "title": "TestApp", "pid": 501, "process_name": "test.exe", "is_minimized": True, "is_maximized": False}

    with patch.object(svc, "find_window", return_value=(mock_win, [mock_win])), \
         patch("win32gui.ShowWindow") as mock_show, \
         patch.object(svc._user32, "IsIconic", return_value=0), \
         patch("win32gui.SetForegroundWindow"):

        res = svc.restore_window("TestApp")
        assert res["success"] is True
        assert res["verified"] is True
        assert "restored" in res["message"].lower()
        mock_show.assert_called_once()


def test_maximize_window_verified():
    svc = DesktopControlService()
    mock_win = {"hwnd": 1001, "title": "TestApp", "pid": 501, "process_name": "test.exe", "is_minimized": False, "is_maximized": False}

    with patch.object(svc, "find_window", return_value=(mock_win, [mock_win])), \
         patch("win32gui.ShowWindow") as mock_show, \
         patch.object(svc._user32, "IsZoomed", return_value=1), \
         patch("win32gui.SetForegroundWindow"):

        res = svc.maximize_window("TestApp")
        assert res["success"] is True
        assert res["verified"] is True
        assert "maximized" in res["message"].lower()
        mock_show.assert_called_once()


# =============================================================================
# 5. Graceful Close Behavior (WM_CLOSE without kill)
# =============================================================================
def test_graceful_close_sends_wm_close():
    svc = DesktopControlService()
    mock_win = {"hwnd": 1001, "title": "TestApp", "pid": 501, "process_name": "test.exe", "is_minimized": False, "is_maximized": False}

    with patch.object(svc, "find_window", return_value=(mock_win, [mock_win])), \
         patch("win32gui.PostMessage") as mock_post, \
         patch("win32gui.IsWindow", return_value=False):

        res = svc.request_close_window("TestApp")
        assert res["success"] is True
        assert res["verified"] is True
        assert "closed" in res["message"].lower()
        # Ensure WM_CLOSE (0x0010) was posted
        mock_post.assert_called_with(1001, 0x0010, 0, 0)


# =============================================================================
# 6. Unsaved-Work Prompts Detected (Never auto-clicks Save/Discard)
# =============================================================================
def test_unsaved_work_prompt_detection():
    svc = DesktopControlService()
    mock_win = {"hwnd": 1001, "title": "Untitled - Notepad", "pid": 501, "process_name": "notepad.exe", "is_minimized": False, "is_maximized": False}

    with patch.object(svc, "find_window", return_value=(mock_win, [mock_win])), \
         patch("win32gui.PostMessage"), \
         patch("win32gui.IsWindow", return_value=True):

        res = svc.request_close_window("Untitled - Notepad")
        assert res["success"] is True
        assert res["verified"] is True
        assert res.get("prompt_detected") is True
        assert "unsaved changes" in res["message"].lower()


# =============================================================================
# 7. Windows Permission Failures Handled Gracefully
# =============================================================================
def test_permission_failure_reported():
    svc = DesktopControlService()
    mock_win = {"hwnd": 9999, "title": "System Critical", "pid": 4, "process_name": "System", "is_minimized": False, "is_maximized": False}

    with patch.object(svc, "find_window", return_value=(mock_win, [mock_win])), \
         patch("win32gui.ShowWindow", side_effect=PermissionError("Access is denied (5)")):

        res = svc.minimize_window("System Critical")
        assert res["success"] is False
        assert "denied" in res["message"].lower() or "error" in res["message"].lower()


# =============================================================================
# 8. ActionRegistry Rejection of Unauthorized and Arbitrary Commands
# =============================================================================
def test_action_registry_rejects_arbitrary_shell_and_scripts():
    registry = get_action_registry()

    # Permitted desktop operations
    assert registry.is_action_allowed("open_application") is True
    assert registry.is_action_allowed("minimize_window") is True
    assert registry.is_action_allowed("restore_window") is True
    assert registry.is_action_allowed("maximize_window") is True
    assert registry.is_action_allowed("close_window") is True
    assert registry.is_action_allowed("get_system_overview") is True

    # Prohibited operations must be rejected
    prohibited_actions = [
        "execute_shell",
        "bash",
        "powershell",
        "cmd",
        "run_script",
        "eval",
        "exec",
        "system",
        "spawn_process",
        "kill_process",
        "format_disk",
        "edit_registry",
        "write_registry",
    ]

    for bad_act in prohibited_actions:
        assert registry.is_action_allowed(bad_act) is False


# =============================================================================
# 9. ActionRegistry Rejection of Arbitrary File Write / Delete Operations
# =============================================================================
def test_action_registry_rejects_file_write_and_deletion():
    registry = get_action_registry()

    dangerous_file_ops = [
        "write_file",
        "delete_file",
        "remove_file",
        "unlink",
        "rmdir",
        "delete_folder",
        "clear_directory",
        "truncate_file",
        "modify_system_file",
    ]

    for bad_op in dangerous_file_ops:
        assert registry.is_action_allowed(bad_op) is False


# =============================================================================
# 10. Verification of Actual Action Results (ToolResult Structure)
# =============================================================================
def test_desktop_tools_return_structured_result():
    mock_res = {
        "action": "minimize_window",
        "target": "Notepad",
        "success": True,
        "verified": True,
        "message": "Notepad window was minimized.",
    }

    mock_svc = MagicMock()
    mock_svc.minimize_window.return_value = mock_res

    with patch("app.tools.desktop_tools.get_desktop_service", return_value=mock_svc):
        tool_res = minimize_window("Notepad")
        assert tool_res.success is True
        assert tool_res.data["action"] == "minimize_window"
        assert tool_res.data["verified"] is True
        assert "Notepad" in tool_res.summary


# =============================================================================
# 11. Spoken Confirmations via Assistant
# =============================================================================
def test_spoken_confirmations_for_desktop_actions():
    assistant = ZeroAssistant()
    assistant.initialize()
    assistant.wake()

    mock_open_res = {
        "action": "open_application",
        "target": "Notepad",
        "success": True,
        "verified": True,
        "message": "Launched Notepad.",
    }

    with patch("app.services.desktop_control.get_desktop_service") as mock_get_svc:
        mock_svc = MagicMock()
        mock_svc.open_application.return_value = mock_open_res
        mock_get_svc.return_value = mock_svc

        with patch("app.tools.desktop_tools.get_desktop_service", return_value=mock_svc):
            res = assistant.process_input("open notepad")
            assert "launched notepad" in res["reply_text"].lower() or "opened notepad" in res["reply_text"].lower()
            assert res.get("spoken_text") is not None
            assert "notepad" in res["spoken_text"].lower()


def test_spoken_confirmation_for_failed_action():
    assistant = ZeroAssistant()
    assistant.initialize()
    assistant.wake()

    mock_fail_res = {
        "action": "open_application",
        "target": "UninstalledApp",
        "success": False,
        "verified": False,
        "message": "Application 'UninstalledApp' could not be found among installed or registered applications.",
    }

    with patch("app.services.desktop_control.get_desktop_service") as mock_get_svc:
        mock_svc = MagicMock()
        mock_svc.open_application.return_value = mock_fail_res
        mock_get_svc.return_value = mock_svc

        with patch("app.tools.desktop_tools.get_desktop_service", return_value=mock_svc):
            res = assistant.process_input("open UninstalledApp")
            assert "could not be found" in res["reply_text"].lower()
            spoken = res.get("spoken_text") or res["reply_text"]
            assert "could not be found" in spoken.lower()
