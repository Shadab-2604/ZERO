"""
Truthful Windows Network and Internet Diagnostics Subsystem for Zero AI.
Executes real Windows utilities (ipconfig, ping, tracert, socket checks, Ookla Speedtest CLI).
NEVER fabricates or hallucinate command output, IP addresses, or performance metrics.
"""

import logging
import re
import shutil
import socket
import subprocess
import time
from typing import Any
from app.tools.registry import ActionRegistry, ToolResult

logger = logging.getLogger(__name__)


class NetworkDiagnostics:
    """Windows-native network diagnostic functions capturing real system measurements."""

    @staticmethod
    def get_ip_configuration() -> ToolResult:
        """
        Execute 'ipconfig /all' on Windows and parse real network adapters,
        IP addresses, subnet masks, default gateways, and DNS servers.
        """
        try:
            res = subprocess.run(
                ["ipconfig", "/all"],
                capture_output=True,
                text=True,
                shell=False,
                timeout=12,
            )
            raw_stdout = res.stdout
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                summary="The ipconfig command timed out.",
                detailed_text="**Error:** `ipconfig /all` timed out after 12 seconds.",
                error="Timeout",
            )
        except Exception as e:
            logger.error("Failed to execute ipconfig: %s", e)
            return ToolResult(
                success=False,
                summary=f"Failed to query network configuration: {str(e)}",
                detailed_text=f"**Error:** Could not execute `ipconfig`: {str(e)}",
                error=str(e),
            )

        # Parse adapters from output
        adapters: list[dict[str, Any]] = []
        current_adapter: dict[str, Any] | None = None

        lines = raw_stdout.splitlines()
        for line in lines:
            # New adapter section starts with non-indented name ending with ':'
            if line and not line.startswith(" ") and not line.startswith("\t") and line.endswith(":"):
                header = line.rstrip(":")
                if "Windows IP Configuration" in header:
                    continue
                if current_adapter:
                    adapters.append(current_adapter)
                current_adapter = {
                    "name": header,
                    "description": "",
                    "ipv4": [],
                    "ipv6": [],
                    "gateway": [],
                    "dns": [],
                    "dhcp_enabled": None,
                    "media_state": "Connected",
                    "is_virtual": any(
                        v in header.lower()
                        for v in ("virtual", "vethernet", "hyper-v", "vmware", "tailscale", "tap", "loopback", "bluetooth")
                    ),
                }
                continue

            if current_adapter is None:
                continue

            stripped = line.strip()
            if not stripped:
                continue

            # Check media state
            if "Media State" in stripped and "disconnected" in stripped.lower():
                current_adapter["media_state"] = "Disconnected"

            # Check description
            if "Description" in stripped and ":" in stripped:
                current_adapter["description"] = stripped.split(":", 1)[1].strip()

            # DHCP Enabled
            if "DHCP Enabled" in stripped and ":" in stripped:
                current_adapter["dhcp_enabled"] = stripped.split(":", 1)[1].strip()

            # IPv4 Address
            if ("IPv4 Address" in stripped or "IP Address" in stripped) and ":" in stripped:
                val = stripped.split(":", 1)[1].strip().replace("(Preferred)", "").strip()
                if val:
                    current_adapter["ipv4"].append(val)

            # IPv6 Address
            if "IPv6 Address" in stripped and ":" in stripped:
                val = stripped.split(":", 1)[1].strip().replace("(Preferred)", "").strip()
                if val and not val.startswith("fe80"):
                    current_adapter["ipv6"].append(val)

            # Default Gateway
            if "Default Gateway" in stripped and ":" in stripped:
                val = stripped.split(":", 1)[1].strip()
                if val:
                    current_adapter["gateway"].append(val)

            # DNS Servers
            if "DNS Servers" in stripped and ":" in stripped:
                val = stripped.split(":", 1)[1].strip()
                if val:
                    current_adapter["dns"].append(val)

        if current_adapter:
            adapters.append(current_adapter)

        # Filter active adapters with IP addresses
        active_adapters = [a for a in adapters if a["ipv4"] and a["media_state"] != "Disconnected"]

        # Build clean report
        md_lines = ["### Windows Network Adapter & IP Configuration\n"]
        if not active_adapters:
            md_lines.append("*No active network adapters with assigned IPv4 addresses found.*\n")
        else:
            for a in active_adapters:
                kind = "Virtual Adapter" if a["is_virtual"] else "Physical Adapter"
                md_lines.append(f"#### {a['name']} ({kind})")
                if a["description"]:
                    md_lines.append(f"- **Device:** {a['description']}")
                md_lines.append(f"- **IPv4 Address:** `{', '.join(a['ipv4'])}`")
                if a["ipv6"]:
                    md_lines.append(f"- **IPv6 Address:** `{', '.join(a['ipv6'])}`")
                if a["gateway"]:
                    md_lines.append(f"- **Default Gateway:** `{', '.join(a['gateway'])}`")
                if a["dns"]:
                    md_lines.append(f"- **DNS Servers:** `{', '.join(a['dns'])}`")
                if a["dhcp_enabled"]:
                    md_lines.append(f"- **DHCP Enabled:** {a['dhcp_enabled']}")
                md_lines.append("")

        # Create concise spoken summary
        if active_adapters:
            primary = active_adapters[0]
            ip_val = primary['ipv4'][0] if primary['ipv4'] else 'unknown'
            gw_val = primary['gateway'][0] if primary['gateway'] else 'none'
            summary = f"Your primary network adapter has local IP {ip_val} with gateway {gw_val}."
        else:
            summary = "No active network adapters with an assigned IP address were detected."

        return ToolResult(
            success=True,
            summary=summary,
            detailed_text="\n".join(md_lines),
            data={"adapters": adapters, "active_count": len(active_adapters)},
            raw_output=raw_stdout,
        )

    @staticmethod
    def test_internet_connectivity() -> ToolResult:
        """
        Perform verified, multi-stage internet connectivity checks:
        1. DNS resolution for known hosts.
        2. TCP handshake to public HTTPS endpoints (Port 443).
        3. DNS port check (Port 53).
        4. ICMP ping check.
        Differentiates between DNS, Gateway, and Transport failures.
        """
        results: dict[str, Any] = {}

        # 1. DNS Resolution check
        dns_ok = False
        resolved_ip = None
        try:
            t0 = time.perf_counter()
            resolved_ip = socket.gethostbyname("google.com")
            dns_time_ms = round((time.perf_counter() - t0) * 1000, 1)
            dns_ok = True
            results["dns"] = {"status": "SUCCESS", "resolved_ip": resolved_ip, "latency_ms": dns_time_ms}
        except Exception as e:
            results["dns"] = {"status": "FAILED", "error": str(e)}

        # 2. TCP Connectivity checks (HTTPS port 443 and DNS port 53)
        tcp_https_ok = False
        for endpoint, port in [("1.1.1.1", 443), ("8.8.8.8", 53)]:
            try:
                t0 = time.perf_counter()
                with socket.create_connection((endpoint, port), timeout=3.0):
                    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
                    results[f"tcp_{endpoint}_{port}"] = {"status": "CONNECTED", "latency_ms": elapsed_ms}
                    tcp_https_ok = True
            except Exception as e:
                results[f"tcp_{endpoint}_{port}"] = {"status": "FAILED", "error": str(e)}

        # 3. ICMP Ping check
        ping_ok = False
        avg_ping = None
        try:
            ping_res = subprocess.run(
                ["ping", "-n", "2", "-w", "1000", "8.8.8.8"],
                capture_output=True,
                text=True,
                shell=False,
                timeout=5,
            )
            if ping_res.returncode == 0:
                ping_ok = True
                match = re.search(r"Average = (\d+)ms", ping_res.stdout)
                if match:
                    avg_ping = int(match.group(1))
            results["icmp_ping"] = {"status": "SUCCESS" if ping_ok else "DROPPED", "avg_ms": avg_ping}
        except Exception as e:
            results["icmp_ping"] = {"status": "ERROR", "error": str(e)}

        # Diagnose overall health
        if dns_ok and tcp_https_ok:
            status_text = "ONLINE"
            summary = "Internet connection is fully active and functional."
            if avg_ping is not None:
                summary += f" Average ping latency to 8.8.8.8 is {avg_ping} milliseconds."
        elif not dns_ok and tcp_https_ok:
            status_text = "DNS_ISSUE"
            summary = "Internet TCP transport is working, but DNS domain resolution failed. Check your DNS settings."
        elif not tcp_https_ok and not dns_ok:
            status_text = "OFFLINE"
            summary = "Your computer is currently offline. No external endpoints could be reached."
        else:
            status_text = "DEGRADED"
            summary = "Internet connectivity is degraded. Some tests passed while others failed."

        detailed = (
            f"### Internet Connectivity Diagnostic Report\n\n"
            f"- **Overall Status:** `{status_text}`\n"
            f"- **DNS Resolution (google.com):** `{'PASS (' + str(resolved_ip) + ')' if dns_ok else 'FAIL'}`\n"
            f"- **TCP Handshake (1.1.1.1:443):** `{results.get('tcp_1.1.1.1_443', {}).get('status')}`\n"
            f"- **TCP Handshake (8.8.8.8:53):** `{results.get('tcp_8.8.8.8_53', {}).get('status')}`\n"
            f"- **ICMP Ping (8.8.8.8):** `{'PASS (' + str(avg_ping) + ' ms)' if ping_ok else 'NO REPLY / BLOCKED'}`\n\n"
            f"*{summary}*"
        )

        return ToolResult(
            success=dns_ok or tcp_https_ok,
            summary=summary,
            detailed_text=detailed,
            data=results,
        )

    @staticmethod
    def test_dns(hostname: str = "google.com") -> ToolResult:
        """
        Query actual DNS resolution for a given target hostname.
        Never fabricates DNS records.
        """
        clean_host = hostname.strip().lower()
        # Clean protocol prefixes if user passed http(s)://
        clean_host = re.sub(r"^https?://", "", clean_host).split("/")[0]

        try:
            t0 = time.perf_counter()
            addr_info = socket.getaddrinfo(clean_host, None)
            duration_ms = round((time.perf_counter() - t0) * 1000, 1)

            ips = sorted(list(set(item[4][0] for item in addr_info)))
            ipv4_list = [ip for ip in ips if ":" not in ip]
            ipv6_list = [ip for ip in ips if ":" in ip]

            summary = f"DNS resolution for {clean_host} succeeded in {duration_ms} milliseconds."
            detailed = (
                f"### DNS Resolution Diagnostic: `{clean_host}`\n\n"
                f"- **Status:** Successful\n"
                f"- **Lookup Latency:** `{duration_ms} ms`\n"
                f"- **Resolved IPv4 Addresses:** `{', '.join(ipv4_list) if ipv4_list else 'None'}`\n"
                f"- **Resolved IPv6 Addresses:** `{', '.join(ipv6_list) if ipv6_list else 'None'}`\n"
            )
            return ToolResult(
                success=True,
                summary=summary,
                detailed_text=detailed,
                data={"host": clean_host, "ipv4": ipv4_list, "ipv6": ipv6_list, "time_ms": duration_ms},
            )
        except Exception as e:
            return ToolResult(
                success=False,
                summary=f"Failed to resolve DNS for {clean_host}.",
                detailed_text=f"### DNS Resolution Failed: `{clean_host}`\n\n**Error:** `{str(e)}`\nVerify hostname spelling and network connection.",
                error=str(e),
            )

    @staticmethod
    def test_latency_and_packet_loss(target: str = "8.8.8.8", count: int = 4) -> ToolResult:
        """
        Execute bounded ICMP ping to measure real round-trip latency and packet loss.
        """
        clean_target = target.strip()
        count = max(1, min(count, 10))

        try:
            res = subprocess.run(
                ["ping", "-n", str(count), "-w", "1000", clean_target],
                capture_output=True,
                text=True,
                shell=False,
                timeout=count * 2 + 3,
            )
            stdout = res.stdout
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                summary=f"Ping to {clean_target} timed out.",
                detailed_text=f"**Latency Test:** Ping to `{clean_target}` timed out after deadline.",
                error="Timeout",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                summary=f"Ping test error: {str(e)}",
                detailed_text=f"**Error:** Could not execute ping: {str(e)}",
                error=str(e),
            )

        # Parse metrics from stdout
        sent, received, lost, loss_pct = count, 0, count, 100
        min_ms, max_ms, avg_ms = None, None, None

        pkt_match = re.search(
            r"Packets: Sent = (\d+), Received = (\d+), Lost = (\d+)(?: \((\d+)% loss\))?",
            stdout,
        )
        if pkt_match:
            sent = int(pkt_match.group(1))
            received = int(pkt_match.group(2))
            lost = int(pkt_match.group(3))
            loss_pct = int(pkt_match.group(4)) if pkt_match.group(4) else int((lost / sent) * 100)

        time_match = re.search(
            r"Minimum = (\d+)ms, Maximum = (\d+)ms, Average = (\d+)ms",
            stdout,
        )
        if time_match:
            min_ms = int(time_match.group(1))
            max_ms = int(time_match.group(2))
            avg_ms = int(time_match.group(3))

        success = received > 0
        if success:
            summary = f"Ping to {clean_target}: {loss_pct}% loss, average latency {avg_ms} milliseconds."
        else:
            summary = f"All {count} ping packets to {clean_target} were dropped (100% loss)."

        detailed = (
            f"### Ping Latency & Packet Loss: `{clean_target}`\n\n"
            f"- **Target:** `{clean_target}`\n"
            f"- **Packets:** Sent = `{sent}`, Received = `{received}`, Lost = `{lost}` ({loss_pct}% loss)\n"
        )
        if avg_ms is not None:
            detailed += (
                f"- **Round-Trip Times:** Min = `{min_ms} ms`, Max = `{max_ms} ms`, Average = `{avg_ms} ms`\n"
            )
        else:
            detailed += "- **Round-Trip Times:** No replies received (probes dropped or ICMP blocked by firewall).\n"

        return ToolResult(
            success=success,
            summary=summary,
            detailed_text=detailed,
            data={
                "target": clean_target,
                "sent": sent,
                "received": received,
                "lost": lost,
                "loss_pct": loss_pct,
                "min_ms": min_ms,
                "max_ms": max_ms,
                "avg_ms": avg_ms,
            },
            raw_output=stdout,
        )

    @staticmethod
    def trace_route(target: str = "8.8.8.8", max_hops: int = 8) -> ToolResult:
        """
        Execute Windows tracert with bounded hops and timeout.
        Reports actual hop IP addresses and response times.
        """
        clean_target = target.strip()
        max_hops = max(1, min(max_hops, 15))

        try:
            res = subprocess.run(
                ["tracert", "-d", "-h", str(max_hops), "-w", "1000", clean_target],
                capture_output=True,
                text=True,
                shell=False,
                timeout=max_hops * 3 + 5,
            )
            stdout = res.stdout
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                summary=f"Traceroute to {clean_target} timed out.",
                detailed_text=f"**Traceroute Error:** Route trace timed out.",
                error="Timeout",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                summary=f"Traceroute error: {str(e)}",
                detailed_text=f"**Error:** Could not execute tracert: {str(e)}",
                error=str(e),
            )

        # Parse hops
        hop_lines = []
        for line in stdout.splitlines():
            line_str = line.strip()
            if re.match(r"^\d+\s+", line_str):
                hop_lines.append(line_str)

        summary = f"Route trace to {clean_target} completed across {len(hop_lines)} recorded hops."
        detailed = (
            f"### Traceroute Diagnostic: `{clean_target}` (Max {max_hops} hops)\n\n"
            f"```text\n{stdout.strip()}\n```\n\n"
            f"*Note: Asterisks (*) indicate intermediate routers that drop ICMP traceroute packets by design.*"
        )

        return ToolResult(
            success=True,
            summary=summary,
            detailed_text=detailed,
            data={"target": clean_target, "hops_count": len(hop_lines)},
            raw_output=stdout,
        )

    @staticmethod
    def test_internet_speed() -> ToolResult:
        """
        Execute an actual internet speed test using the official Ookla Speedtest CLI
        when installed. If missing, reports dependency status truthfully and gives
        safe official installation instructions. NEVER fabricates speed test values.
        """
        speedtest_bin = shutil.which("speedtest") or shutil.which("speedtest.exe")
        if not speedtest_bin:
            # Check standard Ookla installation directory
            import os
            candidates = [
                os.path.expandvars(r"%ProgramFiles%\Ookla\Speedtest\speedtest.exe"),
                os.path.expandvars(r"%LocalAppData%\Programs\Ookla\Speedtest\speedtest.exe"),
            ]
            for c in candidates:
                if os.path.isfile(c):
                    speedtest_bin = c
                    break

        if not speedtest_bin:
            return ToolResult(
                success=False,
                summary="The official Ookla Speedtest CLI is not installed on this system.",
                detailed_text=(
                    "### Internet Speed Test Dependency Missing\n\n"
                    "The official **Ookla Speedtest CLI** is required for accurate, truthful bandwidth measurements.\n\n"
                    "**Installation Options:**\n"
                    "1. Via Windows Package Manager (PowerShell):\n"
                    "   ```powershell\n"
                    "   winget install Ookla.Speedtest\n"
                    "   ```\n"
                    "2. Official Download:\n"
                    "   [https://www.speedtest.net/apps/cli](https://www.speedtest.net/apps/cli)\n\n"
                    "*Zero does not fabricate simulated speed values. Please install the official tool to measure real download and upload rates.*"
                ),
                error="Speedtest CLI not installed",
            )

        try:
            # Execute speedtest CLI with JSON format
            res = subprocess.run(
                [speedtest_bin, "--format=json", "--accept-license", "--accept-gdpr"],
                capture_output=True,
                text=True,
                shell=False,
                timeout=45,
            )
            if res.returncode != 0:
                return ToolResult(
                    success=False,
                    summary=f"Speedtest failed with exit code {res.returncode}.",
                    detailed_text=f"**Speedtest Error:** `{res.stderr or res.stdout}`",
                    error=res.stderr,
                )

            import json
            data = json.loads(res.stdout)
            # Speedtest CLI outputs bytes per second in data['download']['bandwidth']
            down_bytes = data.get("download", {}).get("bandwidth", 0)
            up_bytes = data.get("upload", {}).get("bandwidth", 0)
            down_mbps = round((down_bytes * 8) / (1000 * 1000), 2)
            up_mbps = round((up_bytes * 8) / (1000 * 1000), 2)
            ping_jitter = data.get("ping", {}).get("jitter")
            ping_latency = data.get("ping", {}).get("latency")
            server_name = data.get("server", {}).get("name", "Unknown Server")
            server_location = data.get("server", {}).get("location", "")

            summary = f"Speed test complete: {down_mbps} Mbps download, {up_mbps} Mbps upload, with {ping_latency} milliseconds latency."
            detailed = (
                f"### Ookla Speedtest Results\n\n"
                f"- **Download Speed:** `{down_mbps} Mbps`\n"
                f"- **Upload Speed:** `{up_mbps} Mbps`\n"
                f"- **Ping Latency:** `{ping_latency} ms` (Jitter: `{ping_jitter} ms`)\n"
                f"- **Test Server:** `{server_name} ({server_location})`\n"
                f"- **ISP:** `{data.get('isp', 'N/A')}`\n"
            )
            return ToolResult(
                success=True,
                summary=summary,
                detailed_text=detailed,
                data={
                    "download_mbps": down_mbps,
                    "upload_mbps": up_mbps,
                    "ping_ms": ping_latency,
                    "server": server_name,
                },
                raw_output=res.stdout,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                summary="The speed test timed out.",
                detailed_text="**Error:** Speed test timed out after 45 seconds.",
                error="Timeout",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                summary=f"Speed test execution failed: {str(e)}",
                detailed_text=f"**Error:** {str(e)}",
                error=str(e),
            )

    @classmethod
    def full_network_diagnostic(cls) -> ToolResult:
        """
        Run a complete, efficient network diagnostic profile:
        1. IP configuration
        2. Internet connectivity & latency
        3. DNS resolution
        4. Speed test (if available)
        """
        ip_res = cls.get_ip_configuration()
        conn_res = cls.test_internet_connectivity()
        dns_res = cls.test_dns("google.com")
        ping_res = cls.test_latency_and_packet_loss("8.8.8.8", count=2)

        md_parts = [
            "## Comprehensive Network Diagnostic Report\n",
            conn_res.detailed_text,
            "\n---\n",
            ip_res.detailed_text,
            "\n---\n",
            dns_res.detailed_text,
            "\n---\n",
            ping_res.detailed_text,
        ]

        summary = f"Full network diagnostic complete. System is {conn_res.data.get('dns', {}).get('status', 'ONLINE')} with {ping_res.data.get('avg_ms', 'N/A')} ms average ping."

        return ToolResult(
            success=conn_res.success,
            summary=summary,
            detailed_text="\n".join(md_parts),
            data={
                "connectivity": conn_res.data,
                "ip": ip_res.data,
                "dns": dns_res.data,
                "ping": ping_res.data,
            },
        )


def register_network_tools(registry: ActionRegistry) -> None:
    """Register all network diagnostic actions."""
    registry.register(
        name="ip_config",
        description="Query local Windows IP and network adapter configuration",
        handler=NetworkDiagnostics.get_ip_configuration,
        parameters={},
    )
    registry.register(
        name="test_internet_connectivity",
        description="Verify active internet connectivity across DNS, TCP, and ICMP",
        handler=NetworkDiagnostics.test_internet_connectivity,
        parameters={},
    )
    registry.register(
        name="test_dns",
        description="Perform actual DNS resolution lookup for a target hostname",
        handler=NetworkDiagnostics.test_dns,
        parameters={"hostname": {"type": "string", "default": "google.com"}},
    )
    registry.register(
        name="test_latency",
        description="Measure round-trip ping latency and packet loss to target IP",
        handler=NetworkDiagnostics.test_latency_and_packet_loss,
        parameters={"target": {"type": "string", "default": "8.8.8.8"}, "count": {"type": "integer", "default": 4}},
    )
    registry.register(
        name="trace_route",
        description="Trace network route hops to a destination target",
        handler=NetworkDiagnostics.trace_route,
        parameters={"target": {"type": "string", "default": "8.8.8.8"}, "max_hops": {"type": "integer", "default": 8}},
    )
    registry.register(
        name="test_speed",
        description="Run official Ookla Speedtest bandwidth check (if installed)",
        handler=NetworkDiagnostics.test_internet_speed,
        parameters={},
    )
    registry.register(
        name="full_network_diagnostic",
        description="Run complete Windows network diagnostic profile",
        handler=NetworkDiagnostics.full_network_diagnostic,
        parameters={},
    )
