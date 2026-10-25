"""
Intent recognition and routing for Zero AI commands, queries, tools, and diagnostics.
"""

from enum import Enum
import re
import logging

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    WAKE = "WAKE"
    SLEEP = "SLEEP"
    BRIEFING = "BRIEFING"
    SUMMARIZE_PREVIOUS = "SUMMARIZE_PREVIOUS"
    SHOW_ACTIVITY = "SHOW_ACTIVITY"
    OPEN_SETTINGS = "OPEN_SETTINGS"
    STOP_SPEAKING = "STOP_SPEAKING"
    CANCEL = "CANCEL"
    REPEAT = "REPEAT"
    QUIT = "QUIT"
    SEARCH_KNOWLEDGE = "SEARCH_KNOWLEDGE"
    REBUILD_KNOWLEDGE = "REBUILD_KNOWLEDGE"
    GENERATE_DOCUMENT = "GENERATE_DOCUMENT"
    TEXT_MODE = "TEXT_MODE"

    # Browser & System Tools
    OPEN_CHROME = "OPEN_CHROME"
    BROWSER_SEARCH = "BROWSER_SEARCH"
    OPEN_URL = "OPEN_URL"

    # Network & System Diagnostics
    DIAGNOSTIC_IP = "DIAGNOSTIC_IP"
    DIAGNOSTIC_INTERNET = "DIAGNOSTIC_INTERNET"
    DIAGNOSTIC_DNS = "DIAGNOSTIC_DNS"
    DIAGNOSTIC_PING = "DIAGNOSTIC_PING"
    DIAGNOSTIC_TRACERT = "DIAGNOSTIC_TRACERT"
    DIAGNOSTIC_SPEED = "DIAGNOSTIC_SPEED"
    DIAGNOSTIC_FULL_NETWORK = "DIAGNOSTIC_FULL_NETWORK"
    DIAGNOSTIC_SYSTEM = "DIAGNOSTIC_SYSTEM"
    DIAGNOSTIC_OLLAMA = "DIAGNOSTIC_OLLAMA"
    DIAGNOSTIC_PDF = "DIAGNOSTIC_PDF"

    # Desktop Automation & Window Control
    DESKTOP_OPEN_APP = "DESKTOP_OPEN_APP"
    DESKTOP_MINIMIZE = "DESKTOP_MINIMIZE"
    DESKTOP_RESTORE = "DESKTOP_RESTORE"
    DESKTOP_MAXIMIZE = "DESKTOP_MAXIMIZE"
    DESKTOP_SWITCH = "DESKTOP_SWITCH"
    DESKTOP_CLOSE = "DESKTOP_CLOSE"
    DESKTOP_LIST_WINDOWS = "DESKTOP_LIST_WINDOWS"
    DESKTOP_LIST_APPS = "DESKTOP_LIST_APPS"
    DESKTOP_SYSTEM_OVERVIEW = "DESKTOP_SYSTEM_OVERVIEW"

    CHAT = "CHAT"


class IntentRouter:
    """Parses text or voice utterances to determine appropriate assistant action."""

    @staticmethod
    def clean_text(text: str) -> str:
        """Strip punctuation and normalize whitespace."""
        cleaned = re.sub(r"[^\w\s]", "", text.lower())
        return " ".join(cleaned.split())

    @classmethod
    def match_intent(cls, utterance: str) -> tuple[IntentType, str]:
        """
        Match utterance to an intent and return (IntentType, matched_clean_query).
        """
        normalized = cls.clean_text(utterance)

        # 1. Quit / Exit Intent
        if normalized in (
            "zero quit", "quit", "exit", "shutdown zero", "close zero", "terminate", "goodbye zero"
        ):
            return IntentType.QUIT, normalized

        # 2. Wake Intent
        if any(
            phrase in normalized
            for phrase in [
                "zero wake up",
                "wake up zero",
                "wake up",
                "zero online",
                "systems on",
            ]
        ):
            return IntentType.WAKE, normalized

        # 3. Sleep Intent
        if any(
            phrase in normalized
            for phrase in [
                "zero sleep",
                "sleep zero",
                "go to sleep",
                "stand down zero",
                "zero stand down",
                "systems down",
            ]
        ):
            return IntentType.SLEEP, normalized

        # 4. Stop Speaking
        if any(
            phrase in normalized
            for phrase in [
                "zero stop speaking",
                "stop speaking",
                "stop talking",
                "be quiet",
                "silence",
                "shut up",
                "halt speech",
            ]
        ):
            return IntentType.STOP_SPEAKING, normalized

        # 5. Repeat That
        if any(
            phrase in normalized
            for phrase in [
                "zero repeat that",
                "repeat that",
                "repeat what you said",
                "say that again",
                "repeat last message",
                "say again",
            ]
        ):
            return IntentType.REPEAT, normalized

        # 6. Rebuild Knowledge
        if any(
            phrase in normalized
            for phrase in [
                "zero rebuild knowledge",
                "rebuild knowledge",
                "rebuild my knowledge",
                "reindex knowledge",
                "reindex documents",
                "rebuild knowledge base",
            ]
        ):
            return IntentType.REBUILD_KNOWLEDGE, normalized

        # 7. Search Knowledge (Check BEFORE general web search)
        if any(
            phrase in normalized
            for phrase in [
                "zero search my knowledge",
                "search my knowledge",
                "search knowledge",
                "search my documents",
                "find in knowledge",
                "search files",
            ]
        ):
            return IntentType.SEARCH_KNOWLEDGE, utterance

        # 8. Diagnostic PDF Export (Check BEFORE general document generation)
        if any(
            p in normalized
            for p in [
                "pdf of my internet diagnostic",
                "pdf of internet diagnostic",
                "pdf of diagnostic report",
                "diagnostic report pdf",
                "create a pdf of my internet diagnostic report",
                "export diagnostic to pdf",
                "diagnostic pdf",
                "network diagnostic pdf",
            ]
        ):
            return IntentType.DIAGNOSTIC_PDF, utterance

        # 9. General Document Generation (HTML -> PDF)
        doc_patterns = [
            "create a report", "generate a report", "make a report",
            "create report", "generate report",
            "create a project plan", "generate a project plan", "make a project plan",
            "create documentation", "generate documentation",
            "create a study guide", "generate a study guide",
            "export as pdf", "generate pdf", "download as pdf", "create pdf",
            "export notes to pdf", "pdf document", "to pdf",
        ]
        if any(p in doc_patterns for p in normalized.split(" and ")):
            return IntentType.GENERATE_DOCUMENT, utterance
        if any(p in normalized for p in doc_patterns):
            return IntentType.GENERATE_DOCUMENT, utterance

        # 10. Network & System Diagnostics (Real Execution)
        # Full network test
        if any(
            p in normalized
            for p in [
                "test everything about my internet",
                "full network diagnostic",
                "complete network diagnostic",
                "test my complete internet connection",
                "test complete internet",
                "diagnose whole network",
                "full internet test",
            ]
        ):
            return IntentType.DIAGNOSTIC_FULL_NETWORK, normalized

        # Speed test
        if any(
            p in normalized
            for p in [
                "test my internet speed",
                "test internet speed",
                "check my download and upload speed",
                "check download speed",
                "check internet speed",
                "speed test",
                "speedtest",
                "test network speed",
            ]
        ):
            return IntentType.DIAGNOSTIC_SPEED, normalized

        # IP Configuration
        if any(
            p in normalized
            for p in [
                "show my ip configuration",
                "show ip configuration",
                "show my ip",
                "what is my local ip address",
                "what is my ip address",
                "my local ip address",
                "what is my ip",
                "check all my network adapters",
                "check network adapters",
                "show my gateway and dns servers",
                "show my gateway and dns",
                "show my gateway",
                "show dns servers",
                "ipconfig",
                "ip config",
                "network configuration",
            ]
        ):
            return IntentType.DIAGNOSTIC_IP, normalized

        # Internet Connectivity
        if any(
            p in normalized
            for p in [
                "check whether my internet is working",
                "is my internet working",
                "test my internet connection",
                "test internet connection",
                "why is my internet not working",
                "check internet",
                "test internet",
                "internet status",
                "am i online",
            ]
        ):
            return IntentType.DIAGNOSTIC_INTERNET, normalized

        # DNS Diagnostics
        if any(
            p in normalized
            for p in [
                "test my dns",
                "test dns",
                "resolve googlecom",
                "resolve google",
                "check my dns servers",
                "dns lookup",
                "dns diagnostic",
            ]
        ):
            return IntentType.DIAGNOSTIC_DNS, utterance

        # Ping & Latency
        if any(
            p in normalized
            for p in [
                "check my ping",
                "test latency and packet loss",
                "test latency",
                "packet loss",
                "check if my connection is unstable",
                "ping test",
                "check ping",
            ]
        ):
            return IntentType.DIAGNOSTIC_PING, utterance

        # Traceroute
        if any(
            p in normalized
            for p in [
                "trace my internet route",
                "trace route",
                "traceroute",
                "show the route to",
                "show route to",
                "diagnose a routing problem",
                "trace hops",
            ]
        ):
            return IntentType.DIAGNOSTIC_TRACERT, utterance

        # Ollama Status
        if any(
            p in normalized
            for p in [
                "check whether ollama is working",
                "is ollama working",
                "check ollama",
                "ollama status",
                "ollama health",
                "installed models",
                "local models working",
            ]
        ):
            return IntentType.DIAGNOSTIC_OLLAMA, normalized

        # System Hardware Status
        if any(
            p in normalized
            for p in [
                "system status",
                "cpu and memory usage",
                "check system status",
                "check hardware",
                "system telemetry",
                "cpu usage",
                "memory usage",
                "disk space",
                "check system",
            ]
        ):
            return IntentType.DIAGNOSTIC_SYSTEM, normalized

        # 11. Browser Actions
        # Open URL
        url_match = re.search(r"\b(open\s+url|navigate\s+to|go\s+to)\s+(https?://\S+)", utterance, re.IGNORECASE)
        if url_match:
            return IntentType.OPEN_URL, url_match.group(2)
        if utterance.strip().startswith(("http://", "https://")):
            return IntentType.OPEN_URL, utterance.strip()

        # Browser Search
        if (
            ("open chrome" in normalized and "search" in normalized)
            or normalized.startswith(("search for ", "google search ", "search google for "))
            or re.search(r"\b(search the web for|search online for|look up on google)\b", normalized)
        ):
            return IntentType.BROWSER_SEARCH, utterance

        # 12. Desktop Automation & Window Control
        # Desktop: List Open Windows
        if any(
            p in normalized
            for p in [
                "show me all currently open applications",
                "show me all open applications",
                "show all open applications",
                "show open applications",
                "show currently open applications",
                "show me all open windows",
                "show open windows",
                "what windows are open",
                "show active windows",
                "list windows",
                "list open windows",
                "open windows",
            ]
        ):
            return IntentType.DESKTOP_LIST_WINDOWS, normalized

        # Desktop: List Running Applications
        if any(
            p in normalized
            for p in [
                "tell me which applications are running",
                "which applications are running",
                "what applications are running",
                "show running applications",
                "show running apps",
                "list running applications",
                "list running apps",
                "running applications",
                "running apps",
            ]
        ):
            return IntentType.DESKTOP_LIST_APPS, normalized

        # Desktop: System Awareness & Overview
        if any(
            p in normalized
            for p in [
                "show my cpu ram disk and network status",
                "show my cpu ram disk and network",
                "show cpu ram disk and network",
                "cpu ram disk and network",
                "show system overview",
                "system overview",
                "system awareness",
                "full system status",
            ]
        ):
            return IntentType.DESKTOP_SYSTEM_OVERVIEW, normalized

        # Desktop: Minimize Window
        m_min = re.search(r"\bminimize\s+(?:the\s+)?([a-zA-Z0-9_\-\.\s]+?)(?:\s+window)?$", normalized)
        if m_min:
            target = m_min.group(1).strip()
            if target and target not in ("window", "windows", "it"):
                return IntentType.DESKTOP_MINIMIZE, target
            elif target in ("window", "it"):
                return IntentType.DESKTOP_MINIMIZE, ""

        # Desktop: Restore Window
        m_res = re.search(r"\b(?:restore|unminimize)\s+(?:the\s+)?([a-zA-Z0-9_\-\.\s]+?)(?:\s+window)?$", normalized)
        if m_res:
            target = m_res.group(1).strip()
            if target and target not in ("window", "windows", "it"):
                return IntentType.DESKTOP_RESTORE, target
            elif target in ("window", "it"):
                return IntentType.DESKTOP_RESTORE, ""

        # Desktop: Maximize Window
        m_max = re.search(r"\bmaximize\s+(?:the\s+)?([a-zA-Z0-9_\-\.\s]+?)(?:\s+window)?$", normalized)
        if m_max:
            target = m_max.group(1).strip()
            if target and target not in ("window", "windows", "it"):
                return IntentType.DESKTOP_MAXIMIZE, target
            elif target in ("window", "it"):
                return IntentType.DESKTOP_MAXIMIZE, ""

        # Desktop: Switch / Focus Window
        m_switch = re.search(r"\b(?:switch to|focus|bring to front|bring to foreground)\s+(?:the\s+)?([a-zA-Z0-9_\-\.\s]+?)(?:\s+window)?$", normalized)
        if m_switch:
            target = m_switch.group(1).strip()
            if target:
                return IntentType.DESKTOP_SWITCH, target

        # Desktop: Close Window
        m_close = re.search(r"\bclose\s+(?:the\s+)?([a-zA-Z0-9_\-\.\s]+?)(?:\s+window)?$", normalized)
        if m_close:
            target = m_close.group(1).strip()
            if target and target not in ("zero", "this", "it"):
                return IntentType.DESKTOP_CLOSE, target

        # Open Chrome (without search)
        if any(
            p in normalized
            for p in ["open chrome", "launch chrome", "start chrome", "open browser", "run chrome"]
        ):
            return IntentType.OPEN_CHROME, normalized

        # Desktop: Open Application (Handles "open Notepad", "open VS Code", etc.)
        m_open = re.search(r"\b(?:open|launch|start|run)\s+(?:the\s+)?([a-zA-Z0-9_\-\.\s]+)$", normalized)
        if m_open:
            app_target = m_open.group(1).strip()
            if app_target not in ("settings", "zero settings", "url", "browser", "document", "knowledge"):
                return IntentType.DESKTOP_OPEN_APP, app_target

        # 13. Cancel
        if any(
            phrase in normalized
            for phrase in ["cancel that", "cancel request", "abort", "never mind"]
        ):
            return IntentType.CANCEL, normalized

        # 13. Briefing
        if any(
            phrase in normalized
            for phrase in [
                "give me todays briefing",
                "give me today briefing",
                "daily briefing",
                "todays briefing",
                "briefing",
                "morning briefing",
                "status briefing",
            ]
        ):
            return IntentType.BRIEFING, normalized

        # 14. Summarize Previous
        if any(
            phrase in normalized
            for phrase in [
                "summarize my previous work",
                "summarize previous work",
                "summarize past work",
                "summarize yesterdays work",
                "summarize yesterday work",
                "summarize previous session",
                "what did we do earlier",
                "what did i do earlier",
                "what were we working on",
                "what did we work on",
                "what did we do last time",
                "what did i do yesterday",
                "what did i do last time",
                "previous session summary",
                "previous work summary",
                "summary of previous work",
                "summary of my previous work",
            ]
        ):
            return IntentType.SUMMARIZE_PREVIOUS, normalized

        # 15. Show Activity
        if any(
            phrase in normalized
            for phrase in [
                "show my project activity",
                "project activity",
                "recent activity",
                "show activity",
                "activity log",
            ]
        ):
            return IntentType.SHOW_ACTIVITY, normalized

        # 16. Open Settings
        if any(
            phrase in normalized
            for phrase in ["open settings", "show settings", "zero settings", "configure zero"]
        ):
            return IntentType.OPEN_SETTINGS, normalized

        # 17. Text mode
        if any(
            phrase in normalized
            for phrase in ["switch to text mode", "text mode", "disable microphone", "mute voice"]
        ):
            return IntentType.TEXT_MODE, normalized

        return IntentType.CHAT, utterance
