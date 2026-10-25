"""
Safe system diagnostics tools for Zero AI.
Monitors OS, CPU, Memory, Disk, Process statistics, and Ollama status.
Provides PDF export integration for diagnostic records.
"""

import logging
import platform
import psutil
import httpx
from app.config.settings import get_settings
from app.tools.registry import ActionRegistry, ToolResult

logger = logging.getLogger(__name__)


class SystemDiagnostics:
    """Safe, read-only system and hardware diagnostic queries."""

    @staticmethod
    def get_system_status() -> ToolResult:
        """Query real CPU, Memory, Disk, and Windows platform telemetry."""
        try:
            # CPU
            cpu_pct = psutil.cpu_percent(interval=0.2)
            cpu_count = psutil.cpu_count(logical=True)
            cpu_freq = psutil.cpu_freq()
            freq_ghz = round(cpu_freq.current / 1000.0, 2) if cpu_freq else None

            # Memory
            mem = psutil.virtual_memory()
            mem_total_gb = round(mem.total / (1024**3), 1)
            mem_used_gb = round(mem.used / (1024**3), 1)
            mem_pct = mem.percent

            # Disk (Primary C: drive)
            disk = psutil.disk_usage("C:\\")
            disk_total_gb = round(disk.total / (1024**3), 1)
            disk_free_gb = round(disk.free / (1024**3), 1)
            disk_pct = disk.percent

            # OS
            os_name = f"Windows {platform.release()} ({platform.version()})"

            summary = f"System is running {os_name} with CPU at {cpu_pct}%, memory at {mem_pct}%, and {disk_free_gb} GB disk space free."
            detailed = (
                f"### Windows System Telemetry\n\n"
                f"- **Operating System:** `{os_name}` ({platform.machine()})\n"
                f"- **CPU Usage:** `{cpu_pct}%` across `{cpu_count}` logical cores"
                + (f" @ `{freq_ghz} GHz`\n" if freq_ghz else "\n")
                + f"- **RAM Usage:** `{mem_used_gb} GB / {mem_total_gb} GB` ({mem_pct}%)\n"
                f"- **Primary Disk (C:):** `{disk_free_gb} GB free / {disk_total_gb} GB` ({disk_pct}% used)\n"
            )

            return ToolResult(
                success=True,
                summary=summary,
                detailed_text=detailed,
                data={
                    "os": os_name,
                    "cpu_pct": cpu_pct,
                    "mem_pct": mem_pct,
                    "disk_free_gb": disk_free_gb,
                },
            )
        except Exception as e:
            logger.error("Error reading system telemetry: %s", e)
            return ToolResult(
                success=False,
                summary=f"Failed to query system telemetry: {str(e)}",
                detailed_text=f"**Error:** Could not query system metrics: {str(e)}",
                error=str(e),
            )

    @staticmethod
    def check_ollama_status() -> ToolResult:
        """Query local Ollama daemon health, latency, and installed models."""
        settings = get_settings()
        base_url = settings.ai_api_base.replace("/v1", "")

        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(f"{base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    models = data.get("models", [])
                    model_names = [m.get("name", "") for m in models if m.get("name")]

                    summary = f"Ollama is online locally at {base_url} with {len(model_names)} models installed."
                    detailed = (
                        f"### Local Ollama Service Status\n\n"
                        f"- **Service State:** `ONLINE`\n"
                        f"- **Endpoint:** `{base_url}`\n"
                        f"- **Active Chat Model:** `{settings.local_chat_model}`\n"
                        f"- **Active Code Model:** `{settings.local_code_model}`\n"
                        f"- **Installed Models ({len(model_names)}):**\n"
                    )
                    for m in model_names:
                        detailed += f"  - `{m}`\n"

                    return ToolResult(
                        success=True,
                        summary=summary,
                        detailed_text=detailed,
                        data={"status": "ONLINE", "models": model_names},
                    )
                else:
                    return ToolResult(
                        success=False,
                        summary=f"Ollama returned HTTP error {res.status_code}.",
                        detailed_text=f"**Ollama Error:** Received HTTP status `{res.status_code}` from `{base_url}`.",
                        error=f"HTTP {res.status_code}",
                    )
        except Exception as e:
            return ToolResult(
                success=False,
                summary="Local Ollama daemon is offline or unreachable.",
                detailed_text=(
                    f"### Ollama Service Offline\n\n"
                    f"Could not reach Ollama at `{base_url}`.\n"
                    f"**Error:** `{str(e)}`\n\n"
                    f"To start Ollama, run `ollama serve` in a terminal."
                ),
                error=str(e),
            )

    @staticmethod
    def create_diagnostic_pdf(report_content: str, title: str = "System & Network Diagnostic Report") -> ToolResult:
        """Generate downloadable PDF report from verified diagnostic text."""
        try:
            from app.exports.pdf_generator import PDFGenerator
            import re
            filename_base = "diagnostic_report_" + re.sub(r"[^\w\-]", "_", title.lower())[:25] + ".pdf"

            html = PDFGenerator.create_html_report(
                title=title,
                body_markdown=report_content,
                subtitle="Captured by Zero AI System Diagnostics",
            )
            pdf_path = PDFGenerator.generate_pdf(html, filename=filename_base)
            file_size_kb = pdf_path.stat().st_size / 1024.0

            summary = f"I have generated your diagnostic PDF report: {pdf_path.name}."
            detailed = (
                f"I have compiled your diagnostic report into a verified PDF document:\n\n"
                f"[ARTIFACT_PDF: {pdf_path.name} | {title}]\n\n"
                f"**Artifact Location:** `exports/{pdf_path.name}` ({file_size_kb:.1f} KB)\n"
                f"Click the download button above to open your report."
            )
            return ToolResult(
                success=True,
                summary=summary,
                detailed_text=detailed,
                data={"path": str(pdf_path), "size_kb": file_size_kb},
            )
        except Exception as e:
            logger.error("Failed to generate diagnostic PDF: %s", e)
            return ToolResult(
                success=False,
                summary=f"Failed to generate diagnostic PDF: {str(e)}",
                detailed_text=f"**PDF Generation Error:** {str(e)}",
                error=str(e),
            )


def register_system_tools(registry: ActionRegistry) -> None:
    """Register system status and diagnostic PDF tools."""
    registry.register(
        name="system_status",
        description="Query local Windows OS, CPU, memory, and disk usage",
        handler=SystemDiagnostics.get_system_status,
        parameters={},
    )
    registry.register(
        name="ollama_status",
        description="Verify local Ollama daemon availability and installed models",
        handler=SystemDiagnostics.check_ollama_status,
        parameters={},
    )
    registry.register(
        name="diagnostic_pdf",
        description="Compile and export a verified PDF of network diagnostic results",
        handler=SystemDiagnostics.create_diagnostic_pdf,
        parameters={"report_content": {"type": "string"}, "title": {"type": "string", "default": "Diagnostic Report"}},
    )
