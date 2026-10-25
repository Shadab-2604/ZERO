"""
Tests for Safe Tool Registry, Browser Actions, and Network Diagnostics.
Verifies real command parsing, security controls, URL validation, and rejection of arbitrary commands.
"""

import json
from unittest.mock import MagicMock, patch
import pytest
from app.tools.registry import ActionRegistry, ToolResult, get_action_registry
from app.tools.browser_tools import (
    find_chrome_executable,
    open_browser_search,
    open_chrome,
    open_url,
)
from app.tools.network_diagnostics import NetworkDiagnostics
from app.tools.system_diagnostics import SystemDiagnostics
from app.core.intent_router import IntentRouter, IntentType
from app.core.assistant import get_assistant


def test_registry_registration_and_execution():
    """Verify registry enforces allowlisting and schema validation."""
    reg = ActionRegistry()

    def dummy_handler(msg: str = "ok"):
        return ToolResult(success=True, summary=f"Done {msg}", detailed_text=f"Detailed {msg}")

    reg.register(
        name="test_tool",
        description="A dummy test tool",
        handler=dummy_handler,
        parameters={"msg": {"type": "string"}},
    )

    assert reg.is_registered("test_tool") is True
    assert reg.is_registered("unregistered_cmd") is False

    # Execute valid
    res = reg.execute("test_tool", msg="hello")
    assert res.success is True
    assert "Done hello" in res.summary

    # Reject unregistered arbitrary command
    res_unknown = reg.execute("rmdir_c_drive")
    assert res_unknown.success is False
    assert "not registered" in res_unknown.detailed_text


def test_browser_url_validation():
    """Verify open_url rejects non-http/https schemes."""
    # Invalid schemes
    res1 = open_url("file:///etc/passwd")
    assert res1.success is False
    assert "Invalid web address" in res1.summary

    res2 = open_url("javascript:alert(1)")
    assert res2.success is False

    # Valid scheme
    with patch("subprocess.Popen") as mock_popen, patch("app.tools.browser_tools.find_chrome_executable", return_value="C:\\chrome.exe"):
        mock_proc = MagicMock()
        mock_proc.pid = 1234
        mock_popen.return_value = mock_proc

        res_valid = open_url("https://www.google.com")
        assert res_valid.success is True
        assert res_valid.data["pid"] == 1234


def test_browser_search_url_encoding():
    """Verify open_browser_search URL encodes query properly."""
    with patch("subprocess.Popen") as mock_popen, patch("app.tools.browser_tools.find_chrome_executable", return_value="C:\\chrome.exe"):
        mock_proc = MagicMock()
        mock_proc.pid = 5678
        mock_popen.return_value = mock_proc

        res = open_browser_search("Python decorators & generators")
        assert res.success is True
        assert "Python+decorators+%26+generators" in res.data["url"]


def test_browser_search_missing_query():
    """Verify open_browser_search prompts user when query is missing."""
    with patch("app.tools.browser_tools.open_chrome") as mock_chrome:
        mock_chrome.return_value = ToolResult(
            success=True, summary="Opened Chrome", detailed_text="Opened Chrome"
        )
        res = open_browser_search("")
        assert res.success is True
        assert "What would you like to search for?" in res.summary


def test_browser_intent_detection():
    """Verify natural-language queries correctly match browser intents."""
    # 1. Open Chrome
    intent, _ = IntentRouter.match_intent("Zero, open Chrome")
    assert intent == IntentType.OPEN_CHROME

    # 2. Open Chrome with search query
    intent, query = IntentRouter.match_intent("Zero, open Chrome and search Python decorators")
    assert intent == IntentType.BROWSER_SEARCH

    # 3. Open Chrome for me and search (missing query)
    intent, query = IntentRouter.match_intent("Zero, open Chrome for me and search")
    assert intent == IntentType.BROWSER_SEARCH

    # 4. Search Google for Node.js streams
    intent, query = IntentRouter.match_intent("Search for Node.js streams")
    assert intent == IntentType.BROWSER_SEARCH

    # 5. Extract query with question mark
    from app.core.assistant import ZeroAssistant
    q_empty = ZeroAssistant._extract_search_query("Zero, can you just open Chrome for me and search?")
    assert q_empty == ""

    q_with_term = ZeroAssistant._extract_search_query("Zero, open Chrome and search Python decorators?")
    assert q_with_term == "Python decorators"


def test_ip_config_parsing():
    """Verify NetworkDiagnostics.get_ip_configuration parses ipconfig output correctly."""
    mock_ipconfig_out = """
Windows IP Configuration

   Host Name . . . . . . . . . . . . : ZERO-WORKSTATION
   Primary Dns Suffix  . . . . . . . : 
   Node Type . . . . . . . . . . . . : Hybrid
   IP Routing Enabled. . . . . . . . : No

Wireless LAN adapter Wi-Fi:

   Connection-specific DNS Suffix  . : lan
   Description . . . . . . . . . . . : Intel(R) Wi-Fi 6 AX201 160MHz
   Physical Address. . . . . . . . . : 00-11-22-33-44-55
   DHCP Enabled. . . . . . . . . . . : Yes
   IPv4 Address. . . . . . . . . . . : 192.168.1.50(Preferred)
   Subnet Mask . . . . . . . . . . . : 255.255.255.0
   Default Gateway . . . . . . . . . : 192.168.1.1
   DNS Servers . . . . . . . . . . . : 192.168.1.1
                                       8.8.8.8
"""
    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = mock_ipconfig_out
        mock_run.return_value = mock_proc

        res = NetworkDiagnostics.get_ip_configuration()
        assert res.success is True
        assert res.data["active_count"] == 1
        assert "192.168.1.50" in res.summary
        assert "192.168.1.1" in res.summary


def test_ping_latency_and_packet_loss_calculation():
    """Verify ping parsing and metrics calculation."""
    mock_ping_out = """
Pinging 8.8.8.8 with 32 bytes of data:
Reply from 8.8.8.8: bytes=32 time=12ms TTL=115
Reply from 8.8.8.8: bytes=32 time=14ms TTL=115
Reply from 8.8.8.8: bytes=32 time=11ms TTL=115
Reply from 8.8.8.8: bytes=32 time=13ms TTL=115

Ping statistics for 8.8.8.8:
    Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),
Approximate round trip times in milli-seconds:
    Minimum = 11ms, Maximum = 14ms, Average = 12ms
"""
    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = mock_ping_out
        mock_run.return_value = mock_proc

        res = NetworkDiagnostics.test_latency_and_packet_loss("8.8.8.8", count=4)
        assert res.success is True
        assert res.data["sent"] == 4
        assert res.data["received"] == 4
        assert res.data["lost"] == 0
        assert res.data["loss_pct"] == 0
        assert res.data["avg_ms"] == 12


def test_speedtest_missing_cli_handling():
    """Verify speed test reports missing dependency truthfully and never fakes values."""
    with patch("shutil.which", return_value=None), patch("os.path.isfile", return_value=False):
        res = NetworkDiagnostics.test_internet_speed()
        assert res.success is False
        assert "not installed" in res.summary
        assert "winget install Ookla.Speedtest" in res.detailed_text
        assert "speed" not in res.data  # No fabricated speed


def test_speedtest_json_parsing():
    """Verify speedtest JSON output is parsed into Mbps correctly."""
    mock_json = {
        "download": {"bandwidth": 12500000},  # 12.5 MB/s = 100 Mbps
        "upload": {"bandwidth": 6250000},     # 6.25 MB/s = 50 Mbps
        "ping": {"latency": 8.5, "jitter": 1.2},
        "server": {"name": "Local ISP", "location": "Testville"},
        "isp": "FastFiber",
    }
    with patch("shutil.which", return_value="C:\\speedtest.exe"), patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = json.dumps(mock_json)
        mock_run.return_value = mock_proc

        res = NetworkDiagnostics.test_internet_speed()
        assert res.success is True
        assert res.data["download_mbps"] == 100.0
        assert res.data["upload_mbps"] == 50.0
        assert res.data["ping_ms"] == 8.5
        assert "100.0 Mbps" in res.summary


def test_system_status_telemetry():
    """Verify SystemDiagnostics queries real system metrics."""
    res = SystemDiagnostics.get_system_status()
    assert res.success is True
    assert "cpu_pct" in res.data
    assert "mem_pct" in res.data
    assert "disk_free_gb" in res.data
    assert "Windows" in res.data["os"]


def test_assistant_dispatches_real_diagnostic_tools():
    """Verify ZeroAssistant processes natural-language diagnostics and executes real tools."""
    assistant = get_assistant()
    assistant.wake()

    # 1. IP Configuration
    res_ip = assistant.process_input("Zero, show my IP configuration")
    assert res_ip["intent"] == IntentType.DIAGNOSTIC_IP.value
    assert "Network Adapter" in res_ip["reply_text"]

    # 2. Ping
    res_ping = assistant.process_input("Check my ping")
    assert res_ping["intent"] == IntentType.DIAGNOSTIC_PING.value
    assert "Ping Latency" in res_ping["reply_text"]

    # 3. System Status
    res_sys = assistant.process_input("System status")
    assert res_sys["intent"] == IntentType.DIAGNOSTIC_SYSTEM.value
    assert "Windows System Telemetry" in res_sys["reply_text"]
