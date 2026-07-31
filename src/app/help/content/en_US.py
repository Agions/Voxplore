"""English built-in help entries."""

from __future__ import annotations

from ..models import HelpTopic

__all__ = ["TOPICS"]


def _topic(
    topic_id: str,
    title: str,
    body: str,
    *,
    category: str,
    summary: str = "",
    tags: tuple[str, ...] = (),
) -> HelpTopic:
    return HelpTopic(
        id=topic_id,
        title=title,
        category=category,
        summary=summary,
        source="built-in:en_US",
        tags=tags,
        body=body,
    )


TOPICS: list[HelpTopic] = [
    # ─────────────── Shortcuts ───────────────
    _topic(
        topic_id="shortcut.command-palette",
        title="Command Palette (Cmd+K / Ctrl+K)",
        category="shortcut",
        summary="Search commands, navigate pages, switch theme or language.",
        tags=("shortcut", "command palette", "search"),
        body=(
            "Press **Cmd+K** (macOS) or **Ctrl+K** (Windows / Linux) to open the palette.\n\n"
            "- Type to fuzzy-match commands (navigation / view / settings / help).\n"
            "- Use Up/Down to pick one, Enter to run, Esc to dismiss.\n"
            "- Type `help` to open the HelpPanel directly."
        ),
    ),
    _topic(
        topic_id="shortcut.toggle-theme",
        title="Switch Theme (tech-dark / dark / light)",
        category="shortcut",
        summary="Search `theme` in the palette or click the toggle in the status bar.",
        tags=("shortcut", "theme", "toggle"),
        body=(
            "Open the palette and search `theme` to cycle between tech-dark / dark / light.\n\n"
            "Selection persists to QSettings and is restored on the next launch."
        ),
    ),
    _topic(
        topic_id="shortcut.help-panel",
        title="Open Help Panel (F1)",
        category="shortcut",
        summary="Slide-out help panel with a TOC on the left and search on the right.",
        tags=("shortcut", "help", "F1"),
        body=(
            "Press **F1** or type `help` in the palette to open the HelpPanel from the right side.\n\n"
            "Use the search box to fuzzy-match across all topics; the left pane groups by category."
        ),
    ),
    _topic(
        topic_id="shortcut.run-pipeline",
        title="Run Pipeline (Ctrl+R)",
        category="shortcut",
        summary="Trigger the currently selected pipeline.",
        tags=("shortcut", "pipeline", "run"),
        body=(
            "On the **New Project** or **Batch Production** page, press **Ctrl+R** (Cmd+R on macOS) to start the selected pipeline.\n\n"
            "Live progress is mirrored to the Dashboard's \"Running Tasks\" card."
        ),
    ),
    _topic(
        topic_id="shortcut.navigate",
        title="Navigate (Alt+1~5)",
        category="shortcut",
        summary="Quickly jump between top-level pages.",
        tags=("shortcut", "navigate"),
        body=(
            "- **Alt+1** — Dashboard\n"
            "- **Alt+2** — New Project\n"
            "- **Alt+3** — Assets\n"
            "- **Alt+4** — Batch Production\n"
            "- **Alt+5** — Settings"
        ),
    ),
    # ─────────────── FAQ ───────────────
    _topic(
        topic_id="faq.first-launch",
        title="What should I do on first launch?",
        category="faq",
        summary="Install → configure AI → import assets → run a pipeline.",
        tags=("first launch", "onboarding", "new"),
        body=(
            "1. **Install FFmpeg** (see `docs/guide/installation.md` for your OS).\n"
            "2. **Configure at least one AI provider** (DeepSeek / Qwen / OpenAI) via Settings → AI or `config/llm.yaml`.\n"
            "3. **Import assets** by dropping video files into the Assets page.\n"
            "4. **Create a project**, pick a template, run the pipeline.\n\n"
            "A 5-step onboarding tour will appear automatically (resettable from Settings)."
        ),
    ),
    _topic(
        topic_id="faq.api-key",
        title="Where do I configure API keys?",
        category="faq",
        summary="Env vars first, then config file, then Settings page.",
        tags=("api", "key", "config"),
        body=(
            "Three layers, in priority order:\n\n"
            "1. **Environment variables** — `DEEPSEEK_API_KEY`, `QWEN_API_KEY`, `OPENAI_API_KEY`, etc.\n"
            "2. **Config file** — `config/llm.yaml` under `providers.*.api_key`.\n"
            "3. **GUI** — Settings → AI Configuration (auto-encrypted on disk).\n\n"
            "Keys are **never** logged in plaintext and never appear in tooltips."
        ),
    ),
    _topic(
        topic_id="faq.video-analysis-slow",
        title="Video analysis is too slow — what now?",
        category="faq",
        summary="Lower the sampling rate, split into chunks, or pick a faster model.",
        tags=("performance", "video", "slow"),
        body=(
            "Long videos (>30 min) often take time. Try:\n\n"
            "- **Sampling rate**: bump frame interval from 1fps to 2fps in Project Settings → Video Analysis.\n"
            "- **Chunking**: split the source into multiple segments and process in parallel.\n"
            "- **Model choice**: switch from `qwen-vl-plus` to `qwen-vl-turbo` or run Ollama locally."
        ),
    ),
    _topic(
        topic_id="faq.export-platform",
        title="How do I export to Douyin / Bilibili / YouTube?",
        category="faq",
        summary="Pick a platform preset; bitrate, codec, and subtitle format auto-apply.",
        tags=("export", "douyin", "bilibili", "youtube"),
        body=(
            "The Export page ships with 8 platform presets (Douyin / Bilibili / YouTube / TikTok / WeChat / Xiaohongshu / Instagram / Twitter). Each preset sets:\n\n"
            "- Resolution & bitrate (H.264 / H.265)\n"
            "- Subtitle format & font (ASS / SRT)\n"
            "- Audio sample rate (44.1kHz / 48kHz)\n\n"
            "Pick one and click `Start Export`. The generated `.draft.json` can be imported into JianYing for fine-tuning."
        ),
    ),
    _topic(
        topic_id="faq.subtitle-out-of-sync",
        title="My subtitles drift from the audio",
        category="faq",
        summary="Check sample rate / regenerate subtitles / use ASS format.",
        tags=("subtitle", "sync", "audio"),
        body=(
            "Common causes and fixes:\n\n"
            "1. Audio sample rate ≠ 44.1kHz → set it to 44.1kHz and regenerate.\n"
            "2. You edited subtitles manually → remove the manual edits, regenerate.\n"
            "3. SRT lost styles → switch to ASS to preserve fonts and positioning."
        ),
    ),
    _topic(
        topic_id="faq.update",
        title="How do I upgrade to the latest version?",
        category="faq",
        summary="Use the command palette, the Upgrade page, or the CLI.",
        tags=("upgrade", "update"),
        body=(
            "Upgrade paths:\n\n"
            "- GUI: left nav → `Upgrade` → `Check for Updates`.\n"
            "- Palette: Cmd+K → `update`.\n"
            "- CLI: `scenefab --update`.\n\n"
            "Upgrades use incremental deltas + SHA256 verification; failures auto-rollback to the previous stable build."
        ),
    ),
    _topic(
        topic_id="faq.privacy",
        title="Are my assets uploaded to the cloud?",
        category="faq",
        summary="Local-first; only AI calls leave the machine.",
        tags=("privacy", "local", "upload"),
        body=(
            "SceneFab is strictly **local-first**:\n\n"
            "- Videos, narration, subtitles, and voiceovers stay on disk.\n"
            "- Only AI calls (narration, video analysis, TTS) send data to the respective provider.\n"
            "- Use Edge-TTS caching or F5-TTS offline mode to run fully air-gapped.\n\n"
            "Settings → Privacy lists every outbound endpoint."
        ),
    ),
    # ─────────────── Onboarding ───────────────
    _topic(
        topic_id="onboarding.welcome",
        title="Welcome to SceneFab",
        category="onboarding",
        summary="Five steps to your first successful production.",
        tags=("onboarding", "welcome"),
        body=(
            "Welcome! The five steps below will walk you through your first successful production.\n\n"
            "Press **Esc** any time to skip; you can re-enable the tour from Settings → Help."
        ),
    ),
    _topic(
        topic_id="onboarding.layout",
        title="Layout Overview",
        category="onboarding",
        summary="Top nav + Dashboard + monitor + shortcuts.",
        tags=("onboarding", "layout"),
        body=(
            "The main window has four areas:\n\n"
            "1. **Top nav** — switch between Dashboard / Project / Assets / Batch / Settings.\n"
            "2. **Dashboard** — KPI cards on the left, real-time monitor and shortcuts on the right.\n"
            "3. **Status bar** — CPU / memory / disk gauges plus theme and language toggles.\n"
            "4. **Command palette** — press **Cmd+K** to summon it anywhere."
        ),
    ),
    _topic(
        topic_id="onboarding.drag-video",
        title="Import Your First Video",
        category="onboarding",
        summary="Drop a local video into Assets; scene analysis kicks off automatically.",
        tags=("onboarding", "video", "import"),
        body=(
            "Steps:\n\n"
            "1. Navigate to **Assets**.\n"
            "2. Drag `.mp4` / `.mkv` / `.mov` into the empty area.\n"
            "3. Wait for scene analysis (roughly 1/3 of the video's duration).\n"
            "4. Watch the Dashboard's `Recent Assets` card update in real time."
        ),
    ),
    _topic(
        topic_id="onboarding.configure-ai",
        title="Configure AI Providers",
        category="onboarding",
        summary="At least one LLM key is required before running a pipeline.",
        tags=("onboarding", "ai", "config"),
        body=(
            "Configure AI via Settings → AI or edit `config/llm.yaml`.\n\n"
            "- **DeepSeek** — narration (best cost/quality).\n"
            "- **Qwen / OpenAI** — multimodal video analysis.\n"
            "- **Edge-TTS / F5-TTS** — voiceover (Edge free, F5 optional cloning)."
        ),
    ),
    _topic(
        topic_id="onboarding.run-pipeline",
        title="Run Your First Pipeline",
        category="onboarding",
        summary="Pick a template, run it, watch live progress on the Dashboard.",
        tags=("onboarding", "pipeline", "run"),
        body=(
            "Suggested path:\n\n"
            "1. **New Project** → pick the **Narration** template.\n"
            "2. Choose one of the imported videos plus a prompt.\n"
            "3. Press **Ctrl+R** to start.\n"
            "4. Switch to the Dashboard — the `Running Tasks` card shows step-by-step progress."
        ),
    ),
]
