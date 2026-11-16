from pathlib import Path

import streamlit.components.v1 as components


_voice_component = components.declare_component(
    "shopkeeper_browser_voice",
    path=str(Path(__file__).parent / "voice_component"),
)


def voice_input() -> dict[str, str] | None:
    """Render the browser speech-recognition control."""
    result = _voice_component(default=None, key="shopkeeper_voice_input")
    if isinstance(result, dict):
        transcript = result.get("transcript")
        event_id = result.get("event_id")
        if isinstance(transcript, str) and isinstance(event_id, str):
            return {"transcript": transcript, "event_id": event_id}
    return None
