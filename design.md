# Personal AI Assistant — Design Document

## 1. Overview

A Windows desktop AI assistant (JARVIS-style) that can:
1. Hold natural conversations and answer questions ("what should I do today")
2. Open any app installed on the user's PC by voice/text command ("open CapCut")
3. Remember things about the user over time to give better, more personal answers
4. Be extended with new abilities ("tools") over time

**Platform:** Windows 10/11
**Language:** Python 3.11+
**AI Brain:** Swappable — supports GPT (OpenAI) and Gemini (Google) via a
single unified interface (see section 4.1a)
**Build method:** Vibe coding (AI coding assistant + iterative prompting)

---

## 2. Core Architecture

```
User Input (text, later voice)
        |
        v
  Intent Router (the AI brain decides: chat or tool-call?)
        |
   -----------------
   |               |
Chat Mode      Tool Mode
   |               |
Plain reply    Executes matching tool
                (e.g. open_app, get_weather)
        |
        v
   Response back to user (text, later spoken)
```

The AI brain is given a system prompt describing available tools. When the
user's message needs an action, the model returns a structured tool call
(via the provider's native **tool use / function calling** feature — not
manual string parsing). Python then executes the matching function and,
if needed, sends the result back to the model to form a final reply.

---

## 3. MVP Feature Scope (Build in this order)

| Phase | Feature | Goal |
|-------|---------|------|
| 1 | Text chatbot (GPT or Gemini API) | Core conversation loop working |
| 1.5 | Usage/cost tracking + terminal dashboard | See API spend from day one |
| 2 | App auto-discovery + `open_app` tool | "open capcut" launches CapCut |
| 3 | Local memory (facts + chat history) | Personalized answers over time |
| 4 | More tools (web search, reminders, volume, etc.) | Expand usefulness |
| 5 | Voice input (Whisper) + voice output (TTS) | Speak instead of type |
| 6 | Wake word ("Hey Jarvis") | Hands-free activation |
| 7 | Simple GUI or system tray app | Nicer than raw terminal |

Do not skip ahead — each phase should run and work before starting the next.

---

## 4. Component Breakdown

### 4.1 Intent Router / AI Brain
- Uses the active provider's API (GPT or Gemini) with **tool use** enabled.
- System prompt defines the assistant's persona + lists all available tools
  with descriptions (the model decides when to call them).
- Handles two response types:
  - Plain text → show/speak directly
  - Tool call → run the matching Python function, then optionally send the
    tool result back to the model for a natural-language summary

### 4.1a Multi-Provider Support (GPT / Gemini)

Each provider has its own SDK and its own way of doing tool use, so the
design needs one abstraction layer that hides these differences from the
rest of the app.

**Approach:** build a `LLMProvider` interface with one method, e.g.
`send(messages, tools) -> response`, and one implementation per provider:

```
brain/
├── router.py          # calls whichever provider is active, unaware of details
└── providers/
    ├── base.py         # abstract interface all providers implement
    ├── openai.py        # wraps `openai` SDK (GPT)
    └── gemini.py        # wraps `google-generativeai` SDK
```

Each provider file is responsible for:
1. Formatting the conversation history into that provider's expected shape
2. Formatting the tool schema into that provider's expected shape (tool
   use formats differ slightly between GPT and Gemini)
3. Parsing that provider's response back into one **common internal
   format**, e.g.:
   ```python
   {"type": "text", "content": "..."}
   # or
   {"type": "tool_call", "name": "open_app", "arguments": {"name": "capcut"}}
   ```

The rest of the app (memory, tools, main loop) only ever talks to this
common format — it never needs to know which provider answered.

**Selecting a provider:**
- Store the active provider + API key(s) in `config.py` or a `.env` file
- Simple version: one config value, e.g. `ACTIVE_PROVIDER = "gpt"`
- Nicer version: let the user switch providers with a command, e.g.
  "switch to gemini" — useful for comparing quality/cost/speed, or falling
  back if one provider is down or rate-limited

**API keys needed:**
| Provider | SDK | Env variable (suggested) |
|----------|-----|---------------------------|
| GPT | `openai` | `OPENAI_API_KEY` |
| Gemini | `google-generativeai` | `GEMINI_API_KEY` |

**Build order note:** implement and fully test ONE provider first
(recommend starting with GPT, since tool use is very well documented and
widely used). Once the interface is proven with one provider, adding the
second is mostly repeating the same pattern.

### 4.2 App Discovery & Launcher (`open_app` tool)
**Goal:** works for ANY installed app, no manual list.

**Sources to scan:**
- `C:\ProgramData\Microsoft\Windows\Start Menu\Programs\**\*.lnk`
- `C:\Users\<user>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\**\*.lnk`
- Windows Registry `Uninstall` keys (backup source for exe paths)

**Process:**
1. On startup (or cached + refreshed periodically), scan the folders above.
2. Resolve each `.lnk` shortcut to its target `.exe` path (use `pywin32` /
   `winshell`).
3. Build an in-memory map: `{ "clean app name": "path/to/target.exe" }`
4. Cache this map to a local JSON file so re-scans are fast.
5. When the user says "open X":
   - Fuzzy-match "X" against the app name map (e.g. `rapidfuzz` library)
     to tolerate typos/partial names ("cap cut" → "CapCut")
   - Launch via `subprocess.Popen(path)` or `os.startfile(path)`
   - If no confident match, ask the user to clarify or list close matches

**Refresh trigger:** re-scan on app startup, and optionally on a manual
"refresh my apps" command (covers newly installed apps).

### 4.3 Memory System
Two layers, kept simple at first:

**a) Conversation history**
- Store recent messages (rolling window, e.g. last 20-50 turns) in a local
  JSON or SQLite file.
- Fed back into the API call each turn so context isn't lost.

**b) Long-term facts / preferences**
- A separate store of durable facts about the user (e.g. "user edits video
  with CapCut", "user works out at 7am", "user prefers short answers").
- Can start as a simple JSON file: `{"facts": ["...", "..."]}`.
- After each conversation (or periodically), the AI can be prompted to
  extract new durable facts worth remembering and append them.
- These facts get injected into the system prompt so answers like "what
  should I do today" become genuinely personalized over time.

**Storage recommendation:** start with local JSON files (simplest for a
beginner project). Move to SQLite later if data grows or querying gets
complex.

### 4.4 Tool Library
Each tool = one Python function + a schema description for the model.
Start with:
- `open_app(name: str)` — launch an installed application
- `search_web(query: str)` — quick web search (optional, via a search API)
- `get_weather(city: str)` — current weather
- `set_reminder(text: str, time: str)` — simple local reminder/notification

Design every new tool the same way so adding one is a repeatable pattern:
1. Write the Python function
2. Add its name/description/parameters to the tools list sent to the model
3. Add a case in the "if tool_call, run this function" dispatcher

### 4.5 Voice Layer (Phase 5, later)
- **Speech-to-text:** OpenAI Whisper (local, free, accurate)
- **Text-to-speech:** start with `pyttsx3` (free, offline, robotic) → can
  upgrade later to ElevenLabs API for natural voice
- **Wake word:** Porcupine (Picovoice) for "Hey Jarvis" style activation

### 4.6 Interface (Phase 7, later)
Start fully in terminal. Later options, in order of effort:
- Simple system tray icon (using `pystray`) with a popup text box
- Lightweight GUI (using `customtkinter` or similar)
- Overlay-style always-on-top mini window

### 4.7 Monitoring Dashboard

**Reality check first:** this is a personal, single-user, local assistant
— not a multi-tenant SaaS product. So some of what's below (RAG upload
panels, fine-tuning export, moderation flags) is genuinely useful, but at
a much smaller scale than an enterprise dashboard. Below, each section
notes whether it's **[Core]** (build it, real value for a solo project) or
**[Advanced/Optional]** (nice to have, only build if you actually want
that capability — skip it otherwise, it's a lot of extra work for a
personal tool).

Build in the recommended sub-order within each category — don't try to do
all 5 categories at once.

---

#### A. Executive Overview & KPIs **[Core]**

Top-of-dashboard summary cards:
- **Total AI Activity** — count of chat turns, tool calls executed, and
  distinct "sessions" (a session = one run of the assistant, or a burst
  of activity after idle time)
- **Task success rate** — % of tool calls that completed without error
  (e.g. `open_app` found and launched something vs. failed/no match)
- **Latency** — average response time per request, tracked from "message
  sent" to "response received," broken down by provider (GPT vs Gemini
  often differ meaningfully here)

**"User satisfaction" for a solo project:** a full thumbs up/down system
is more than you need day one. Simple version: after each response, allow
an optional `good`/`bad` quick-tag command (e.g. typing `:bad` right after
a reply logs the last interaction as unsatisfactory). Store this in the
same SQLite DB as everything else. This gives you a real satisfaction
ratio without building a rating UI.

---

#### B. Resource Usage & Financial Tracking **[Core]**

This is what you originally asked for — already covered in detail below,
folded in here as the anchor of the dashboard:

- **Token & API usage** — daily/monthly input & output token charts, per
  provider (see `usage_log` table below)
- **Cost analytics** — running spend vs. a monthly budget you set, with
  an alert when you cross a threshold (e.g. 80%, 100%)
- **Infrastructure health** — for a personal project this simplifies to:
  last successful API call timestamp per provider, current rate-limit
  status if the API returns that info, and count of failed calls in the
  last hour (a spike here means something's wrong — bad key, provider
  outage, or you've hit a quota)

**Data model (SQLite):**
```
usage_log
----------
id
timestamp
provider          # "openai" | "gemini"
model
input_tokens
output_tokens
estimated_cost
tool_called       # nullable
latency_ms
status            # "ok" | "error" | "timeout"
error_message     # nullable
```

This single table backs both the KPI cards (A) and the resource tracking
(B) — no need for a separate table per feature.

---

#### C. Activity Logs & Content Moderation

- **Live interaction log** **[Core]** — a scrolling/paginated view of
  recent prompts + responses, pulled from your existing conversation
  history store. This is just a read view over data you're already
  saving in Phase 3 (memory) — no new logging needed, just a UI for it.
- **Error & fallback tracking** **[Core]** — every API error, timeout, or
  unhandled exception gets logged to `usage_log.status`/`error_message`
  (schema above) and shown as its own filtered view: "show me only
  errors from today."
- **Safety/moderation flags** **[Advanced/Optional]** — for a personal
  assistant talking only to you, a full moderation pipeline is usually
  overkill. If you still want it: OpenAI's API exposes a free moderation
  endpoint you can run responses through, and flagged items get a tag in
  the log. Only worth building if you plan to let other people use this
  assistant too, or if you're piping in untrusted content (e.g. web
  search results) that you want screened.

---

#### D. AI Configuration & Management (Playground) **[Core, simplified]**

A settings panel — doesn't need to be fancy, even a simple form on the
dashboard page works:
- **Model selection & parameters** — dropdown to switch active provider
  (GPT/Gemini) and model, sliders/inputs for temperature and max tokens.
  These write straight to your `.env`/config, taking effect on next
  message (no restart needed if `router.py` re-reads config each call).
- **System prompt editor** — a text box to view/edit the assistant's
  system prompt without touching code. Save it to a `system_prompt.txt`
  file that `router.py` loads at startup — editing it in the dashboard
  just rewrites that file.

---

#### E. Knowledge Base (RAG) & Human-in-the-Loop **[Advanced/Optional]**

These are the two heaviest asks — genuinely useful, but real scope, not a
quick add. Only build if you specifically want the assistant to answer
from your own documents, or you want to formally curate training data.

- **RAG / knowledge base:** upload panel for PDFs/docs → chunk the text →
  embed with a provider's embedding API → store vectors locally (e.g.
  `chromadb`, which runs embedded/local, no separate server needed) →
  retrieve relevant chunks and inject into the system prompt before each
  call. This is effectively a whole extra subsystem — treat it as its own
  build phase, not a dashboard checkbox.
- **Fine-tuning dataset export:** an "annotate this response as
  wrong/right" button in the activity log (C), and an export command that
  dumps tagged pairs to a `.jsonl` file in the format your chosen
  provider's fine-tuning pipeline expects. Only useful once you have
  enough real usage data to make fine-tuning worthwhile — not a v1
  feature.
- **Manual override / takeover:** since this assistant only acts when you
  type/speak to it (no autonomous background workflows in this design),
  there isn't really a "live automated process" to interrupt. This
  becomes relevant only if you later build autonomous/scheduled behaviors
  (e.g. the assistant acting on a timer without you present) — flag it as
  a future consideration, not needed for the current design.

---

#### Suggested Dashboard Build Order

1. **[Core]** SQLite `usage_log` table + logging wired into `router.py`
2. **[Core]** Terminal dashboard (`rich`) showing KPIs (A) + usage/cost (B)
3. **[Core]** Web dashboard (Flask/FastAPI + Chart.js) once terminal
   version feels limiting — same data, nicer charts, and gives you a
   natural home for (C) log viewer and (D) config panel
4. **[Core]** Activity log viewer + error view (C, minus moderation)
5. **[Core, simplified]** Config panel — model/params + system prompt
   editor (D)
6. **[Advanced/Optional]** Moderation flags, RAG knowledge base,
   fine-tuning export, manual override — pick only what you actually need

---

## 5. Suggested Folder Structure

```
jarvis-assistant/
├── main.py                # entry point, runs the chat loop
├── dashboard/
│   ├── terminal_dashboard.py  # rich-based terminal KPI/usage view
│   ├── web/                    # optional Flask/FastAPI app
│   │   ├── app.py
│   │   ├── templates/
│   │   └── static/
│   ├── config_panel.py         # model/params + system prompt editor
│   └── rag/                     # [optional] knowledge base ingestion
│       └── ingest.py
├── config.py               # loads settings/keys from .env
├── system_prompt.txt        # editable via dashboard config panel
├── pricing.json             # per-provider, per-model token pricing
├── .env                    # actual API keys (NEVER committed to git)
├── .env.example             # template showing required keys, safe to commit
├── .gitignore
├── brain/
│   ├── router.py            # sends messages to active provider, logs usage
│   ├── providers/
│   │   ├── base.py           # shared interface
│   │   ├── openai.py
│   │   └── gemini.py
│   └── tools.py             # tool schemas + dispatcher
├── tools/
│   ├── app_launcher.py      # app discovery + open_app logic
│   ├── weather.py
│   └── reminders.py
├── memory/
│   ├── history.py           # conversation history read/write
│   └── facts.py             # long-term facts read/write
├── usage/
│   └── tracker.py           # log_usage(), cost calc, budget checks, KPI queries
├── data/
│   ├── apps_cache.json      # cached discovered apps
│   ├── history.json
│   ├── facts.json
│   └── app.db                # SQLite: usage_log, feedback_tags tables
└── requirements.txt
```

---

## 6. GitHub / Secrets Hygiene

Since this project will be pushed to a GitHub repo, API keys and personal
data must never be committed. Set this up from the very first commit —
not after you've already pushed a key by accident.

### `.env` — your real secrets (never committed)
```
OPENAI_API_KEY=your-real-key-here
GEMINI_API_KEY=your-real-key-here
ACTIVE_PROVIDER=openai
```
Load it in `config.py` using the `python-dotenv` package:
```python
from dotenv import load_dotenv
import os

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
```

### `.env.example` — safe template, DOES get committed
So anyone (including future you) knows what keys are needed, with no real
values:
```
OPENAI_API_KEY=
GEMINI_API_KEY=
ACTIVE_PROVIDER=openai
```

### `.gitignore`
At minimum, include:
```
# secrets
.env

# python
__pycache__/
*.pyc
.venv/
venv/

# local data / cache (personal to your PC, shouldn't be public)
data/apps_cache.json
data/history.json
data/facts.json
data/app.db

# OS junk
.DS_Store
Thumbs.db
```

**If you ever accidentally commit a real API key:** don't just delete it
in a new commit — it stays in git history. Revoke/regenerate that key from
the provider's dashboard immediately, then remove it from history if
needed (e.g. `git filter-repo` or GitHub's guide on removing sensitive
data).

---

## 7. Key Libraries

| Purpose | Library |
|---------|---------|
| AI brain — GPT | `openai` |
| AI brain — Gemini | `google-generativeai` |
| Fuzzy app name matching | `rapidfuzz` |
| Shortcut (.lnk) resolving | `pywin32` or `winshell` |
| Local storage | built-in `json`, or `sqlite3` for later |
| Usage/cost dashboard (terminal) | `rich` |
| Usage/cost dashboard (web, optional) | `flask` or `fastapi` + Chart.js |
| RAG knowledge base (optional) | `chromadb` (local vector store) |
| Speech-to-text (later) | `openai-whisper` |
| Text-to-speech (later) | `pyttsx3` (or ElevenLabs API later) |
| Wake word (later) | `pvporcupine` |
| Tray/GUI (later) | `pystray`, `customtkinter` |

---

## 8. Non-Goals (for now)

- The AI will **not** rewrite its own code or self-modify — "improvement"
  means: more memory + more manually/vibe-coded tools, not autonomous
  self-editing.
- No cloud sync/multi-device support in v1 — everything local to one PC.
- No mobile app in v1.

---

## 9. First Build Prompt (for the vibe-coding tool)

> "Build a Python command-line assistant on Windows. It should:
> 1. Use the [OpenAI GPT / Google Gemini — pick one to start] API with tool
>    use enabled for a conversation loop in the terminal. Structure the
>    code so the AI provider is behind a simple interface (one
>    `send(messages, tools)` function) so I can add support for the other
>    provider later without rewriting the rest of the app.
> 2. Include a tool called `open_app` that scans Windows Start Menu
>    shortcuts to build a map of installed app names to their executable
>    paths, caches this map as JSON, and uses fuzzy matching to open the
>    closest match when the user says something like 'open capcut'.
> 3. Store conversation history in a local JSON file and include the last
>    ~20 messages as context in each API call.
> Set it up so I just add my API key(s) to a config file and run one
> command to start chatting."

---

## 10. Milestones Checklist

- [x] Phase 1: Terminal chatbot responds correctly
- [x] Phase 1.5a: `usage_log` table + logging wired into every API call
- [x] Phase 1.5b: Terminal dashboard shows KPIs + token/cost usage
- [x] Phase 1.5c: Budget alert triggers when spend crosses threshold
- [x] Phase 2: "open [app name]" reliably opens the right app
- [x] Phase 3: Assistant recalls facts from earlier conversations
- [ ] Phase 3.5: Dashboard activity log viewer shows recent prompts/responses
- [x] Phase 4: At least 2-3 more tools working (weather, reminders, search)
- [x] Phase 5: Can talk to it and hear it talk back
- [x] Phase 6: Wake word activates listening
- [x] Phase 7: Runs from system tray, not just terminal
- [ ] Phase 7.5 (optional): Web dashboard replaces terminal dashboard
- [ ] Phase 7.5 (optional): Config panel — switch model/params, edit system prompt live
- [ ] Phase 8 (optional): RAG knowledge base for document-grounded answers
- [ ] Phase 8 (optional): Feedback tagging + fine-tuning dataset export
