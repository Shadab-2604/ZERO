"""
Zero AI core assistant controller coordinating state, intents, briefings, tools, and conversations.
"""

import logging
import re
from typing import Callable
from app.config.settings import get_settings
from app.core.state_manager import StateManager, AssistantState
from app.core.intent_router import IntentRouter, IntentType
from app.core.briefing_service import BriefingService
from app.core.conversation_manager import ConversationManager
from app.memory.activity_store import ActivityStore
from app.memory.conversation_store import ConversationStore
from app.tools import get_action_registry

logger = logging.getLogger(__name__)


class ZeroAssistant:
    """Central engine of the Zero AI desktop assistant."""

    def __init__(self):
        self.state_manager = StateManager(initial_state=AssistantState.SLEEPING)
        self.briefing_service = BriefingService()
        self.conversation_manager = ConversationManager()
        self.active_session_id: str | None = None
        self.active_conversation_id: str | None = None
        self._speech_stop_callback: Callable[[], None] | None = None
        self._last_assistant_response: str = ""
        self._last_diagnostic_report: str = ""

    def initialize(self) -> None:
        """Start assistant session and initialize default conversation."""
        self.active_session_id = ActivityStore.start_session()
        conv = ConversationStore.get_or_create_latest_conversation()
        self.active_conversation_id = conv.id
        logger.info(
            "ZeroAssistant initialized. Session: %s, Conversation: %s",
            self.active_session_id,
            self.active_conversation_id,
        )

    def set_speech_stop_callback(self, callback: Callable[[], None]) -> None:
        """Register hook to stop active audio playback."""
        self._speech_stop_callback = callback

    def wake(self, force_briefing: bool = False) -> str:
        """
        Transition assistant to READY or LISTENING, greet user, and deliver briefing.
        """
        self.state_manager.transition_to(AssistantState.READY, reason="Wake requested")
        settings = get_settings()

        response_text = ""
        if settings.briefing_on_wake:
            briefing = self.briefing_service.generate_briefing(force=force_briefing)
            response_text = briefing["text"]
        else:
            response_text = "Zero is awake and ready. How may I help you?"

        ActivityStore.record_activity("session", "Assistant awakened.")
        self._last_assistant_response = response_text
        return response_text

    def sleep(self) -> str:
        """
        Transition assistant to SLEEPING and stop active audio.
        """
        if self._speech_stop_callback:
            try:
                self._speech_stop_callback()
            except Exception as e:
                logger.error("Error invoking speech stop callback: %s", e)

        self.state_manager.transition_to(AssistantState.SLEEPING, reason="Sleep requested")
        ActivityStore.record_activity("session", "Assistant entered sleep mode.")
        reply = "Going to sleep. Say 'Zero, wake up' when you need me."
        self._last_assistant_response = reply
        return reply

    def stop_speaking(self) -> str:
        """Interrupt and silence any active speech."""
        if self._speech_stop_callback:
            try:
                self._speech_stop_callback()
            except Exception as e:
                logger.error("Error interrupting speech: %s", e)
        if self.state_manager.current_state == AssistantState.SPEAKING:
            self.state_manager.transition_to(AssistantState.READY, reason="Speech stopped")
        return "Speech interrupted."

    def repeat_last_response(self) -> str:
        """Return the previous assistant response."""
        return self._last_assistant_response or "There is no previous response to repeat."

    @staticmethod
    def _extract_search_query(text: str) -> str:
        """Extract user search query from utterance, or return empty string if missing."""
        clean = text.strip()
        clean = re.sub(r"(?i)^(zero\s*,?\s*)?(can\s+you\s+)?(just\s+)?(please\s+)?", "", clean).strip()
        # Strip trailing punctuation
        clean_no_punct = clean.rstrip("?.! ").strip()

        # Check "open chrome for me and search"
        if re.search(r"(?i)open\s+chrome\s+(for\s+me\s+)?and\s+search\s*$", clean_no_punct):
            return ""

        # Check "open chrome and search (for)? <query>"
        m = re.search(r"(?i)open\s+chrome\s+(for\s+me\s+)?and\s+search\s*(for\s+)?(.*)", clean_no_punct)
        if m:
            extracted = m.group(3).strip().rstrip("?.! ")
            return extracted if extracted else ""

        # Check "search (the web|google|online)? for <query>"
        m = re.search(
            r"(?i)^(google\s+search|search\s+google|search\s+for|search\s+the\s+web\s+for|search\s+online\s+for|search)\s*(for\s+)?(.*)",
            clean_no_punct,
        )
        if m:
            extracted = m.group(3).strip().rstrip("?.! ")
            return extracted if extracted else ""

        return ""

    @staticmethod
    def _extract_hostname(text: str) -> str:
        """Extract target hostname for DNS queries."""
        m = re.search(r"\b(resolve|lookup|dns\s+for)\s+([a-zA-Z0-9\.\-]+)", text, re.IGNORECASE)
        if m:
            return m.group(2).strip()
        return "google.com"

    @staticmethod
    def _extract_ip_or_host(text: str, default: str = "8.8.8.8") -> str:
        """Extract target IP or hostname for ping/tracert."""
        m = re.search(r"\b(ping|route\s+to|target)\s+([a-zA-Z0-9\.\-]+)", text, re.IGNORECASE)
        if m:
            val = m.group(2).strip()
            if val not in ("test", "latency", "my", "internet", "route"):
                return val
        return default

    def _handle_generate_document(self, prompt: str) -> str:
        """Generate content, compile HTML, and export a verified PDF artifact."""
        from app.exports.pdf_generator import PDFGenerator

        clean_title = re.sub(
            r"(?i)^(create|generate|make|export)\s+(a\s+|an\s+)?(report|document|documentation|study\s+guide|project\s+plan|pdf)\s*(on|about|for)?\s*",
            "",
            prompt.strip(),
        ).strip()
        doc_title = clean_title.title() if clean_title else "Executive Intelligence Report"
        filename_base = re.sub(r"[^\w\-]", "_", doc_title.lower())[:30] + ".pdf"

        doc_prompt = (
            f"Generate a comprehensive, beautifully structured executive document for: '{doc_title}'.\n"
            f"Include:\n"
            f"1. Executive Summary\n"
            f"2. Core Architecture & Key Concepts\n"
            f"3. Structured Analysis Table\n"
            f"4. Code Implementation Example with syntax highlighting where relevant\n"
            f"5. Next Action Items\n\n"
            f"Use clean Markdown formatting with headings (##, ###), tables, bullet points, and code blocks."
        )

        try:
            content, _ = self.conversation_manager.process_user_message(
                conversation_id=self.active_conversation_id or "default",
                message_text=doc_prompt,
            )
            clean_content = content.replace("[DEMO MODE]", "").strip()

            html = PDFGenerator.create_html_report(
                title=doc_title,
                body_markdown=clean_content,
                subtitle="Generated by Zero AI Subsystem",
            )
            pdf_path = PDFGenerator.generate_pdf(html, filename=filename_base)
            file_size_kb = pdf_path.stat().st_size / 1024.0

            ActivityStore.record_activity("artifact", f"Generated PDF report: {pdf_path.name}")

            return (
                f"I have compiled your document and rendered the verified PDF artifact:\n\n"
                f"[ARTIFACT_PDF: {pdf_path.name} | {doc_title}]\n\n"
                f"**Artifact Location:** `exports/{pdf_path.name}` ({file_size_kb:.1f} KB)\n"
                f"Click the download button above to open the PDF directly."
            )
        except Exception as e:
            logger.error("Failed to generate PDF document: %s", e)
            return f"Failed to generate PDF artifact: {str(e)}"

    def process_input(self, user_text: str) -> dict:
        """
        Process incoming user text or transcription, route intents, execute tools,
        and generate response.
        Returns dict with: intent, reply_text, state, conversation_id, and optional spoken_text.
        """
        user_text = user_text.strip()
        if not user_text:
            return {
                "intent": IntentType.CHAT.value,
                "reply_text": "I didn't catch that.",
                "spoken_text": "I didn't catch that.",
                "state": self.state_manager.current_state.value,
            }

        intent, matched_query = IntentRouter.match_intent(user_text)
        logger.info("Matched intent: %s for input '%s'", intent.value, user_text)

        # 1. Quit Intent
        if intent == IntentType.QUIT:
            farewell = self.sleep()
            return {
                "intent": intent.value,
                "reply_text": farewell,
                "spoken_text": farewell,
                "state": AssistantState.SLEEPING.value,
                "conversation_id": self.active_conversation_id,
            }

        # 2. Wake intent
        if intent == IntentType.WAKE:
            reply = self.wake()
            return {
                "intent": intent.value,
                "reply_text": reply,
                "spoken_text": reply,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # 3. Sleep intent
        if intent == IntentType.SLEEP:
            reply = self.sleep()
            return {
                "intent": intent.value,
                "reply_text": reply,
                "spoken_text": reply,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # If sleeping, ignore ordinary requests unless woken
        if self.state_manager.current_state == AssistantState.SLEEPING:
            return {
                "intent": "IGNORED_WHILE_SLEEPING",
                "reply_text": "Zero is currently sleeping. Say 'Zero, wake up' or tap the wake button to begin.",
                "spoken_text": "Zero is sleeping. Say Zero, wake up to begin.",
                "state": AssistantState.SLEEPING.value,
                "conversation_id": self.active_conversation_id,
            }

        # 4. Stop speaking
        if intent == IntentType.STOP_SPEAKING:
            reply = self.stop_speaking()
            return {
                "intent": intent.value,
                "reply_text": reply,
                "spoken_text": "",
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # 5. Repeat that
        if intent == IntentType.REPEAT:
            reply = self.repeat_last_response()
            return {
                "intent": intent.value,
                "reply_text": reply,
                "spoken_text": reply,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # 6. Rebuild Knowledge
        if intent == IntentType.REBUILD_KNOWLEDGE:
            from app.knowledge import get_knowledge_service
            report = get_knowledge_service().sync_and_index(force_all=True)
            reply = (
                f"Knowledge base rebuild complete.\n\n"
                f"• Scanned: {report.scanned_files} files\n"
                f"• Indexed: {report.indexed_files + report.updated_files} files\n"
                f"• Total searchable chunks: {report.total_chunks}\n"
                f"• Rejected media: {report.rejected_files}\n"
                f"• Errors: {report.error_files}"
            )
            spoken = f"Knowledge base rebuild complete. Indexed {report.total_chunks} searchable chunks across {report.scanned_files} files."
            self._last_assistant_response = reply
            ActivityStore.record_activity("tool", f"Rebuilt knowledge base ({report.total_chunks} chunks).")
            return {
                "intent": intent.value,
                "reply_text": reply,
                "spoken_text": spoken,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # 7. Search Knowledge
        if intent == IntentType.SEARCH_KNOWLEDGE:
            from app.knowledge import get_knowledge_service
            clean_q = re.sub(
                r"(?i)^(zero\s+)?(search\s+my\s+knowledge|search\s+knowledge|search\s+documents|search\s+files)\s*(for\s+)?",
                "",
                user_text,
            ).strip()
            search_query = clean_q or user_text
            results = get_knowledge_service().search(search_query, limit=4)
            if not results:
                reply = f"No matching passages found in Knowledge base for '{search_query}'. Place documents in Knowledge/ and say 'Zero, rebuild knowledge'."
                spoken = f"No matching passages found in your knowledge base for {search_query}."
            else:
                lines = [f"Found {len(results)} relevant passages in your Knowledge base for '{search_query}':\n"]
                for i, r in enumerate(results, 1):
                    lines.append(f"• **[Doc: {r.source_file}]** ({r.section_label})\n  > {r.content[:160]}...\n")
                reply = "\n".join(lines)
                spoken = f"I found {len(results)} relevant passages in your knowledge base for {search_query}."
            self._last_assistant_response = reply
            return {
                "intent": intent.value,
                "reply_text": reply,
                "spoken_text": spoken,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # 8. Browser: Open Chrome
        if intent == IntentType.OPEN_CHROME:
            reg = get_action_registry()
            res = reg.execute("open_chrome")
            if res.success:
                ActivityStore.record_activity("tool", "Opened Google Chrome browser.")
            self._last_assistant_response = res.detailed_text
            return {
                "intent": intent.value,
                "reply_text": res.detailed_text,
                "spoken_text": res.summary,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # 9. Browser: Search
        if intent == IntentType.BROWSER_SEARCH:
            query = self._extract_search_query(user_text)
            reg = get_action_registry()
            res = reg.execute("open_browser_search", query=query)
            if res.success and query:
                ActivityStore.record_activity("tool", f"Executed browser search for '{query}'.")
            self._last_assistant_response = res.detailed_text
            return {
                "intent": intent.value,
                "reply_text": res.detailed_text,
                "spoken_text": res.summary,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # 10. Browser: Open URL
        if intent == IntentType.OPEN_URL:
            reg = get_action_registry()
            res = reg.execute("open_url", url=matched_query)
            if res.success:
                ActivityStore.record_activity("tool", f"Navigated to web address: {matched_query}")
            self._last_assistant_response = res.detailed_text
            return {
                "intent": intent.value,
                "reply_text": res.detailed_text,
                "spoken_text": res.summary,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # Desktop: Open Application
        if intent == IntentType.DESKTOP_OPEN_APP:
            reg = get_action_registry()
            res = reg.execute("open_application", app_name=matched_query)
            if res.success:
                ActivityStore.record_activity("tool", f"Opened application: {matched_query}")
            self._last_assistant_response = res.detailed_text
            return {
                "intent": intent.value,
                "reply_text": res.detailed_text,
                "spoken_text": res.summary,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # Desktop: Minimize Window
        if intent == IntentType.DESKTOP_MINIMIZE:
            reg = get_action_registry()
            res = reg.execute("minimize_window", identifier=matched_query)
            if res.success:
                ActivityStore.record_activity("tool", f"Minimized window: {matched_query}")
            self._last_assistant_response = res.detailed_text
            return {
                "intent": intent.value,
                "reply_text": res.detailed_text,
                "spoken_text": res.summary,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # Desktop: Restore Window
        if intent == IntentType.DESKTOP_RESTORE:
            reg = get_action_registry()
            res = reg.execute("restore_window", identifier=matched_query)
            if res.success:
                ActivityStore.record_activity("tool", f"Restored window: {matched_query}")
            self._last_assistant_response = res.detailed_text
            return {
                "intent": intent.value,
                "reply_text": res.detailed_text,
                "spoken_text": res.summary,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # Desktop: Maximize Window
        if intent == IntentType.DESKTOP_MAXIMIZE:
            reg = get_action_registry()
            res = reg.execute("maximize_window", identifier=matched_query)
            if res.success:
                ActivityStore.record_activity("tool", f"Maximized window: {matched_query}")
            self._last_assistant_response = res.detailed_text
            return {
                "intent": intent.value,
                "reply_text": res.detailed_text,
                "spoken_text": res.summary,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # Desktop: Switch / Focus Window
        if intent == IntentType.DESKTOP_SWITCH:
            reg = get_action_registry()
            res = reg.execute("focus_window", identifier=matched_query)
            if res.success:
                ActivityStore.record_activity("tool", f"Switched to window: {matched_query}")
            self._last_assistant_response = res.detailed_text
            return {
                "intent": intent.value,
                "reply_text": res.detailed_text,
                "spoken_text": res.summary,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # Desktop: Close Window
        if intent == IntentType.DESKTOP_CLOSE:
            reg = get_action_registry()
            res = reg.execute("close_window", identifier=matched_query)
            if res.success:
                ActivityStore.record_activity("tool", f"Closed window: {matched_query}")
            self._last_assistant_response = res.detailed_text
            return {
                "intent": intent.value,
                "reply_text": res.detailed_text,
                "spoken_text": res.summary,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # Desktop: List Open Windows
        if intent == IntentType.DESKTOP_LIST_WINDOWS:
            reg = get_action_registry()
            res = reg.execute("list_open_windows")
            self._last_assistant_response = res.detailed_text
            return {
                "intent": intent.value,
                "reply_text": res.detailed_text,
                "spoken_text": res.summary,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # Desktop: List Running Applications
        if intent == IntentType.DESKTOP_LIST_APPS:
            reg = get_action_registry()
            res = reg.execute("list_running_applications")
            self._last_assistant_response = res.detailed_text
            return {
                "intent": intent.value,
                "reply_text": res.detailed_text,
                "spoken_text": res.summary,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # Desktop: System Awareness & Overview
        if intent == IntentType.DESKTOP_SYSTEM_OVERVIEW:
            reg = get_action_registry()
            res = reg.execute("get_system_overview")
            self._last_assistant_response = res.detailed_text
            return {
                "intent": intent.value,
                "reply_text": res.detailed_text,
                "spoken_text": res.summary,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # 11. Diagnostic: IP Configuration
        if intent == IntentType.DIAGNOSTIC_IP:
            reg = get_action_registry()
            res = reg.execute("ip_config")
            self._last_diagnostic_report = res.detailed_text
            if res.success:
                ActivityStore.record_activity("tool", "Queried Windows IP configuration.")
            self._last_assistant_response = res.detailed_text
            return {
                "intent": intent.value,
                "reply_text": res.detailed_text,
                "spoken_text": res.summary,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # 12. Diagnostic: Internet Connectivity
        if intent == IntentType.DIAGNOSTIC_INTERNET:
            reg = get_action_registry()
            res = reg.execute("test_internet_connectivity")
            self._last_diagnostic_report = res.detailed_text
            if res.success:
                ActivityStore.record_activity("tool", "Tested internet connectivity.")
            self._last_assistant_response = res.detailed_text
            return {
                "intent": intent.value,
                "reply_text": res.detailed_text,
                "spoken_text": res.summary,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # 13. Diagnostic: DNS Test
        if intent == IntentType.DIAGNOSTIC_DNS:
            host = self._extract_hostname(user_text)
            reg = get_action_registry()
            res = reg.execute("test_dns", hostname=host)
            self._last_diagnostic_report = res.detailed_text
            self._last_assistant_response = res.detailed_text
            return {
                "intent": intent.value,
                "reply_text": res.detailed_text,
                "spoken_text": res.summary,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # 14. Diagnostic: Ping & Latency
        if intent == IntentType.DIAGNOSTIC_PING:
            target = self._extract_ip_or_host(user_text, default="8.8.8.8")
            reg = get_action_registry()
            res = reg.execute("test_latency", target=target)
            self._last_diagnostic_report = res.detailed_text
            self._last_assistant_response = res.detailed_text
            return {
                "intent": intent.value,
                "reply_text": res.detailed_text,
                "spoken_text": res.summary,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # 15. Diagnostic: Traceroute
        if intent == IntentType.DIAGNOSTIC_TRACERT:
            target = self._extract_ip_or_host(user_text, default="8.8.8.8")
            reg = get_action_registry()
            res = reg.execute("trace_route", target=target)
            self._last_diagnostic_report = res.detailed_text
            self._last_assistant_response = res.detailed_text
            return {
                "intent": intent.value,
                "reply_text": res.detailed_text,
                "spoken_text": res.summary,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # 16. Diagnostic: Speed Test
        if intent == IntentType.DIAGNOSTIC_SPEED:
            reg = get_action_registry()
            res = reg.execute("test_speed")
            self._last_diagnostic_report = res.detailed_text
            if res.success:
                ActivityStore.record_activity("tool", "Executed Ookla Speedtest.")
            self._last_assistant_response = res.detailed_text
            return {
                "intent": intent.value,
                "reply_text": res.detailed_text,
                "spoken_text": res.summary,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # 17. Diagnostic: Full Network Diagnostic
        if intent == IntentType.DIAGNOSTIC_FULL_NETWORK:
            reg = get_action_registry()
            res = reg.execute("full_network_diagnostic")
            self._last_diagnostic_report = res.detailed_text
            ActivityStore.record_activity("tool", "Executed complete network diagnostic profile.")
            self._last_assistant_response = res.detailed_text
            return {
                "intent": intent.value,
                "reply_text": res.detailed_text,
                "spoken_text": res.summary,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # 18. Diagnostic: System Hardware Status
        if intent == IntentType.DIAGNOSTIC_SYSTEM:
            reg = get_action_registry()
            res = reg.execute("system_status")
            self._last_assistant_response = res.detailed_text
            return {
                "intent": intent.value,
                "reply_text": res.detailed_text,
                "spoken_text": res.summary,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # 19. Diagnostic: Ollama Status
        if intent == IntentType.DIAGNOSTIC_OLLAMA:
            reg = get_action_registry()
            res = reg.execute("ollama_status")
            self._last_assistant_response = res.detailed_text
            return {
                "intent": intent.value,
                "reply_text": res.detailed_text,
                "spoken_text": res.summary,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # 20. Diagnostic: PDF Export
        if intent == IntentType.DIAGNOSTIC_PDF:
            reg = get_action_registry()
            if not self._last_diagnostic_report:
                diag_res = reg.execute("full_network_diagnostic")
                self._last_diagnostic_report = diag_res.detailed_text

            res = reg.execute(
                "diagnostic_pdf",
                report_content=self._last_diagnostic_report,
                title="Network & System Diagnostic Report",
            )
            ActivityStore.record_activity("artifact", "Generated diagnostic PDF report.")
            self._last_assistant_response = res.detailed_text
            return {
                "intent": intent.value,
                "reply_text": res.detailed_text,
                "spoken_text": res.summary,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # 21. Generate Document (PDF Export)
        if intent == IntentType.GENERATE_DOCUMENT:
            reply = self._handle_generate_document(user_text)
            self._last_assistant_response = reply
            return {
                "intent": intent.value,
                "reply_text": reply,
                "spoken_text": "I have compiled your document and rendered the verified PDF report.",
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # 22. Cancel
        if intent == IntentType.CANCEL:
            self.stop_speaking()
            self.state_manager.transition_to(AssistantState.READY, reason="Action cancelled")
            return {
                "intent": intent.value,
                "reply_text": "Understood. Action cancelled.",
                "spoken_text": "Understood. Action cancelled.",
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # 23. Briefing request
        if intent == IntentType.BRIEFING:
            briefing = self.briefing_service.generate_briefing(force=True)
            reply = briefing["text"]
            self._last_assistant_response = reply
            return {
                "intent": intent.value,
                "reply_text": reply,
                "spoken_text": reply,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # 24. Summarize previous work
        if intent == IntentType.SUMMARIZE_PREVIOUS:
            summary = ActivityStore.get_latest_session_summary()
            if summary and summary.get("summary_text") and "no external tasks" not in summary["summary_text"].lower():
                reply = f"Here is the summary of your previous session:\n\n{summary['summary_text']}"
            else:
                reply = "No previous session tasks were recorded. As we work, session summaries will appear here."
            self._last_assistant_response = reply
            return {
                "intent": intent.value,
                "reply_text": reply,
                "spoken_text": reply,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # 25. Show Activity
        if intent == IntentType.SHOW_ACTIVITY:
            recent = ActivityStore.get_recent_activities(limit=5)
            verified = [a for a in recent if a.get("category") != "session"]
            if verified:
                acts = [f"• [{a['category']}] {a['description']}" for a in verified]
                reply = "Recent recorded project activity:\n" + "\n".join(acts)
            else:
                reply = "No project activity recorded yet."
            self._last_assistant_response = reply
            return {
                "intent": intent.value,
                "reply_text": reply,
                "spoken_text": reply,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # 26. Open settings
        if intent == IntentType.OPEN_SETTINGS:
            return {
                "intent": intent.value,
                "reply_text": "Opening Zero settings panel.",
                "spoken_text": "Opening Zero settings panel.",
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }

        # 27. General Conversation (with RAG Grounding & Local Models)
        self.state_manager.transition_to(AssistantState.THINKING, reason="Processing AI query")
        try:
            if not self.active_conversation_id:
                conv = ConversationStore.get_or_create_latest_conversation()
                self.active_conversation_id = conv.id

            reply_text, _ = self.conversation_manager.process_user_message(
                conversation_id=self.active_conversation_id,
                message_text=user_text,
            )
            self.state_manager.transition_to(AssistantState.READY, reason="AI response complete")
            self._last_assistant_response = reply_text
            return {
                "intent": IntentType.CHAT.value,
                "reply_text": reply_text,
                "spoken_text": reply_text,
                "state": self.state_manager.current_state.value,
                "conversation_id": self.active_conversation_id,
            }
        except Exception as e:
            logger.error("Error processing user message: %s", e)
            self.state_manager.transition_to(AssistantState.ERROR, reason="Inference error")
            reply_text = f"Error: Unable to process request: {e}"
            self._last_assistant_response = reply_text
            return {
                "intent": IntentType.CHAT.value,
                "reply_text": reply_text,
                "spoken_text": "An error occurred while processing your request.",
                "state": AssistantState.ERROR.value,
                "conversation_id": self.active_conversation_id,
            }

    def shutdown(self) -> None:
        """Gracefully end session, generate truthful summary, and close connections."""
        logger.info("Shutting down ZeroAssistant...")
        if self._speech_stop_callback:
            try:
                self._speech_stop_callback()
            except Exception:
                pass

        if self.active_session_id:
            try:
                recent = ActivityStore.get_recent_activities(limit=10)
                verified_actions = [
                    a["description"] for a in recent
                    if a.get("category") in ("tool", "artifact", "task", "test")
                ]
                if verified_actions:
                    summary_text = (
                        "During this session, the following verified actions were executed: "
                        + "; ".join(verified_actions[:3]) + "."
                    )
                    ActivityStore.save_session_summary(
                        summary_text=summary_text,
                        session_id=self.active_session_id,
                        tasks_completed=verified_actions[:5],
                    )
                else:
                    ActivityStore.save_session_summary(
                        summary_text="Session consisted of conversation and inquiries with Zero. No external tasks were executed.",
                        session_id=self.active_session_id,
                    )
            except Exception as e:
                logger.error("Failed to generate shutdown session summary: %s", e)

            ActivityStore.end_session(self.active_session_id)
            self.active_session_id = None


# Global singleton instance for app-wide sharing between GUI, CLI, and local API
_assistant_instance: ZeroAssistant | None = None


def get_assistant() -> ZeroAssistant:
    """Retrieve global assistant singleton."""
    global _assistant_instance
    if _assistant_instance is None:
        _assistant_instance = ZeroAssistant()
        _assistant_instance.initialize()
    return _assistant_instance
