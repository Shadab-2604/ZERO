# ZERO AI — Features & Operational Capabilities

## Phase 1 Feature Matrix

| Feature | Status | Offline / Demo Ready | Requires API Key / Extra Setup |
|---|---|---|---|
| **JARVIS Desktop GUI** | Built & Tested | Yes (Default) | No |
| **Animated Reactive AI Orb** | Built & Tested | Yes (Default) | No |
| **Assistant State Machine** | Built & Tested | Yes (Default) | No |
| **Wake & Sleep Commands** | Built & Tested | Yes (Default) | No |
| **Timezone-Aware Greeting** | Built & Tested | Yes (Default) | No |
| **Truthful Daily Briefing** | Built & Tested | Yes (Default) | No |
| **Persistent SQLite Storage** | Built & Tested | Yes (Default) | No |
| **Activity & Task Tracking** | Built & Tested | Yes (Default) | No |
| **Session Summaries** | Built & Tested | Yes (Default) | Optional for LLM synthesis |
| **Local REST API (127.0.0.1)** | Built & Tested | Yes (Default) | No |
| **Local Demo AI Provider** | Built & Tested | Yes (Default) | No |
| **Cloud AI Provider (OpenAI/Gemini/Anthropic)** | Built & Tested | No (Fallback to Demo) | Requires `AI_API_KEY` in `.env` |
| **Voice Synthesis (TTS)** | Built & Tested | Yes (Windows SAPI5/pyttsx3) | Requires OS audio output device |
| **Push-to-Talk Speech Recognition** | Built & Tested | Yes | Requires working microphone |
| **Continuous Wake-Word Listener** | Built & Tested | Yes | Requires working microphone |
| **Secret Redaction in Logs & UI** | Built & Tested | Yes (Default) | No |
| **Database Backup & Retention** | Built & Tested | Yes (Default) | No |

---

## Detailed Feature Descriptions

### 1. Cinematic AI Orb & HUD Interface
- **State-Driven Visuals**:
  - `SLEEPING`: Low-frequency soft emerald glow at reduced opacity (resting state).
  - `READY`: Steady neon green core glow with gentle orbital arcs.
  - `LISTENING`: Cyan/teal high-amplitude reactive pulsation responding to voice input.
  - `THINKING`: Rapid azure rotation with orbital HUD arcs indicating inference.
  - `SPEAKING`: Audio-reactive breathing expansion synchronized with speech playback.
  - `ERROR`: Crimson alert ring with diagnostic guidance.
- **HUD Telemetry**: Live ticking chrono, CPU usage, RAM allocation, database connectivity, and active tasks.

### 2. Zero Wake & Sleep Engine
- **Wake Up**:
  - Command: `"Zero, wake up"` or click the **Wake Up** button / AI Orb.
  - Transitions to `READY`.
  - Brightens the orb and activates interface elements.
  - Delivers a personalized, timezone-aware greeting.
  - Issues the daily briefing if not already delivered in the current session.
  - Speaks the response if voice is enabled.
- **Sleep**:
  - Command: `"Zero, sleep"` or click the **Sleep** button.
  - Halts active speech synthesis immediately.
  - Transitions to `SLEEPING`.
  - Dims the orb to resting mode.
  - Frees unnecessary microphone and CPU resources while keeping the background API alive.

### 3. Truthful Briefings & Memory Tracking
- Grounded strictly in real SQLite records:
  - If it is the user's first launch: *"This is your first recorded session. Your project history and activity will appear here as we work."*
  - Summarizes prior sessions without inventing phantom tasks or fabricated history.
  - Lists pending tasks with priority levels.
  - Reports subsystem health status.
  - Asks whether to resume the last pending objective or start a new task.

### 4. Non-Blocking Voice Pipeline
- Microphone listening and speech synthesis run in dedicated worker threads with Windows COM isolation.
- Push-to-talk button provides an immediate voice command trigger without requiring continuous microphone streaming.
- Microphone mute switch disables listening at the hardware driver level.
- Voice interruption (`"Zero, stop speaking"`) halts audio playback immediately.

### 5. Multi-Mode Local REST API
- Binds to `127.0.0.1:8765` by default.
- Provides REST endpoints for remote automation, mobile companion apps, or local scripts to interact with the same state machine and database as the GUI.
