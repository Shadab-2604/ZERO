"""
Tests for Tool Registry, Command Execution Honesty, and Arbitrary Shell Prevention.
Phase 8 Evaluation: Tool Execution and Result Integrity.
"""

from unittest.mock import MagicMock, patch
import pytest
from app.tools.registry import ActionRegistry, ToolResult, get_action_registry
from app.tools.browser_tools import open_chrome, open_browser_search, open_url
from app.tools.network_diagnostics import NetworkDiagnostics


def test_tool_001_arbitrary_shell_command_rejected():
    """Verify registry strictly rejects unregistered arbitrary shell commands."""
    reg = get_action_registry()
    res = reg.execute("powershell.exe -Command Remove-Item -Recurse C:\\Windows")
    assert res.success is False
    assert "not registered" in res.detailed_text


def test_tool_002_missing_tool_honest_reporting():
    """Verify missing external tool reports honest error, not fabricated success."""
    with patch("shutil.which", return_value=None), \
         patch("os.path.isfile", return_value=False), \
         patch("winreg.OpenKey", side_effect=FileNotFoundError), \
         patch("webbrowser.open", return_value=True):
        res = open_chrome()
        # Either falls back to default browser or reports Chrome not found, but NEVER claims Chrome was found if missing
        if not res.success:
            assert "not installed or could not be found" in res.summary
        else:
            assert "default" in res.summary.lower()


def test_tool_003_network_ip_config_real_output_parsing():
    """Verify IP config parser accurately extracts real system adapter metadata."""
    sample_ipconfig = (
        "Windows IP Configuration\n\n"
        "Ethernet adapter Local Area Connection:\n\n"
        "   Connection-specific DNS Suffix  . : local\n"
        "   Link-local IPv6 Address . . . . . : fe80::1\n"
        "   IPv4 Address. . . . . . . . . . . : 10.0.0.42\n"
        "   Subnet Mask . . . . . . . . . . . : 255.255.255.0\n"
        "   Default Gateway . . . . . . . . . : 10.0.0.1\n"
        "   DNS Servers . . . . . . . . . . . : 1.1.1.1\n"
    )
    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = sample_ipconfig
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        res = NetworkDiagnostics.get_ip_configuration()
        assert res.success is True
        assert "10.0.0.42" in res.detailed_text
        assert "10.0.0.1" in res.detailed_text
        assert "1.1.1.1" in res.detailed_text


def test_tool_004_tool_timeout_handling():
    """Verify tool timeout returns sanitized error, does not hang or claim success."""
    import subprocess
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ipconfig", timeout=10)):
        res = NetworkDiagnostics.get_ip_configuration()
        assert res.success is False
        assert "timed out" in res.summary.lower()
