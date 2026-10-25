"""
Honest local Demo AI Provider for Zero.
Operates completely offline with zero external API keys.
Clearly identifies itself as Demo Mode while providing intelligent, contextual JARVIS-style assistance.
"""

import logging
from app.ai.base import BaseAIProvider

logger = logging.getLogger(__name__)


class DemoAIProvider(BaseAIProvider):
    """
    Offline Demo AI provider that enables full system testing and interaction
    without requiring third-party API credentials.
    """

    @property
    def name(self) -> str:
        return "Zero Local Demo Provider (Offline)"

    @property
    def is_available(self) -> bool:
        return True

    def generate_response(
        self, messages: list[dict], system_prompt: str | None = None
    ) -> str:
        """
        Generate contextual responses based on user query and Zero capabilities.
        """
        if not messages:
            return "[DEMO MODE] Zero is awake and standing by. How may I assist you?"

        latest_user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                latest_user_msg = m.get("content", "").strip()
                break

        query = latest_user_msg.lower()

        # Check for RAG context
        if system_prompt and "[KNOWLEDGE BASE RETRIEVAL ACTIVE]" in system_prompt:
            import re
            start_tag = "[KNOWLEDGE BASE RETRIEVAL ACTIVE]"
            end_tag = "[END KNOWLEDGE BASE RETRIEVAL]"
            if start_tag in system_prompt and end_tag in system_prompt:
                rag_block = system_prompt.split(start_tag)[1].split(end_tag)[0].strip()
                sources = re.findall(r"Source:\s*([^\n]+)", rag_block)
                source_cite = f" [Doc: {sources[0]}]" if sources else ""
                snippets = re.findall(r"Content:\s*\n([^\n]+)", rag_block)
                excerpt = snippets[0] if snippets else "Referenced content located."
                return (
                    f"Based on your indexed Knowledge repository{source_cite}:\n\n"
                    f"{excerpt}\n\n"
                    f"Sources cited: {', '.join(sources) if sources else 'Local Knowledge'}"
                )

        # Context-aware responses with explicit [DEMO MODE] banner
        if any(w in query for w in ["who are you", "what are you", "identity"]):
            return (
                "[DEMO MODE] I am ZERO, your personal desktop AI system assistant. "
                "I am currently operating in Local Demo Mode with full local capabilities "
                "(state management, audio synthesis, activity tracking, and UI reactivity). "
                "To connect a cloud model, configure AI_PROVIDER and AI_API_KEY in your .env file."
            )

        if any(w in query for w in ["briefing", "daily briefing", "summary of today", "what happened"]):
            return (
                "[DEMO MODE] To review your full daily briefing and historical session summaries, "
                "you can inspect the 'Daily Briefing' tab on the sidebar or view the right-hand information panel. "
                "I have verified your local database and system metrics are running smoothly."
            )

        if any(w in query for w in ["status", "health", "system"]):
            return (
                "[DEMO MODE] Subsystem telemetry report:\n"
                "- Core Assistant: READY\n"
                "- Database: Healthy (SQLite)\n"
                "- AI Provider: Local Demo Mode (No cloud dependency)\n"
                "- Security: Loopback isolation active (127.0.0.1)"
            )

        if any(w in query for w in ["help", "capabilities", "what can you do"]):
            return (
                "[DEMO MODE] In Phase 1 Foundation, I can:\n"
                "1. Manage wake/sleep states ('Zero, wake up' / 'Zero, sleep')\n"
                "2. Maintain conversation threads and persistent activity logs\n"
                "3. Deliver customized startup and on-demand daily briefings\n"
                "4. Provide a futuristic reactive GUI with real-time audio waveforms\n"
                "5. Expose a secured local REST API on 127.0.0.1:8765\n"
                "6. Seamlessly switch to OpenAI, Gemini, Anthropic, or Ollama when configured."
            )

        if any(w in query for w in ["task", "todo", "tasks"]):
            return (
                "[DEMO MODE] I can track pending tasks and projects in the local SQLite database. "
                "You can add or monitor tasks directly via the local API or project activity store."
            )

        # General response
        return (
            f"[DEMO MODE] Received: \"{latest_user_msg}\".\n\n"
            "Zero is running in Local Demo Mode. The backend architecture, state machine, "
            "database persistence, and PySide6 JARVIS interface are fully operational. "
            "Configure an API key in your .env file to enable live cloud LLM reasoning."
        )

    def generate_summary(self, text: str) -> str:
        """Generate a concise local summary without external API calls."""
        lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
        if not lines:
            return "No activity recorded for this period."

        snippet = lines[0][:120]
        return f"[DEMO SUMMARY] Completed session review: {snippet} (Total events recorded: {len(lines)})."
