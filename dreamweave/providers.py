"""Story and narration providers.

Live providers call xAI (story text) and ElevenLabs (narration). Mock providers
need no keys, so the full app, the tests and the public demo all run for free.
"""

from __future__ import annotations

import io
import json
import math
import struct
import time
import wave
from typing import Iterator, Protocol

import requests


class ProviderError(Exception):
    """An upstream AI provider failed or returned something unusable."""


class StoryModel(Protocol):
    name: str

    def stream(self, system: str, prompt: str) -> Iterator[str]: ...


class Narrator(Protocol):
    name: str
    mimetype: str
    extension: str

    def narrate(self, text: str) -> bytes: ...


class XAIStoryModel:
    name = "xai"

    def __init__(self, api_key: str, url: str, model: str, timeout: float = 60):
        self.api_key = api_key
        self.url = url
        self.model = model
        self.timeout = timeout

    def stream(self, system: str, prompt: str) -> Iterator[str]:
        payload = {
            "model": self.model,
            "stream": True,
            "temperature": 0.8,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        try:
            resp = requests.post(self.url, json=payload, headers=headers, stream=True, timeout=self.timeout)
        except requests.RequestException as exc:
            raise ProviderError(f"story service unreachable: {exc.__class__.__name__}") from exc
        if resp.status_code != 200:
            raise ProviderError(f"story service returned HTTP {resp.status_code}")
        with resp:
            for raw in resp.iter_lines(decode_unicode=True):
                if not raw or not raw.startswith("data:"):
                    continue
                data = raw[5:].strip()
                if data == "[DONE]":
                    return
                try:
                    delta = json.loads(data)["choices"][0].get("delta", {}).get("content")
                except (ValueError, KeyError, IndexError) as exc:
                    raise ProviderError("story service sent malformed data") from exc
                if delta:
                    yield delta


class ElevenLabsNarrator:
    name = "elevenlabs"
    mimetype = "audio/mpeg"
    extension = "mp3"

    def __init__(self, api_key: str, voice_id: str, timeout: float = 90):
        self.api_key = api_key
        self.voice_id = voice_id
        self.timeout = timeout

    def narrate(self, text: str) -> bytes:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
        try:
            resp = requests.post(
                url,
                json={"text": text, "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}},
                headers={"xi-api-key": self.api_key, "Content-Type": "application/json"},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise ProviderError(f"narration service unreachable: {exc.__class__.__name__}") from exc
        if resp.status_code != 200 or not resp.content:
            raise ProviderError(f"narration service returned HTTP {resp.status_code}")
        return resp.content


class MockStoryModel:
    """Deterministic storyteller used for the keyless demo and tests."""

    name = "mock"

    def __init__(self, delay: float = 0.0):
        self.delay = delay

    def stream(self, system: str, prompt: str) -> Iterator[str]:
        hero = _between(prompt, "HERO: ", "\n") or "hero"
        world = _between(prompt, "WORLD: ", "\n") or "faraway land"
        choice = _between(prompt, "READER CHOSE: ", "\n")
        if "TASK: begin" in prompt:
            text = (
                f"Once upon a time, a {hero} lived at the edge of the {world}. "
                f"One morning a glowing map fluttered down and landed at the {hero}'s feet. "
                "It showed two paths: one into a whispering cave, one across a bridge of clouds. "
                "Which path should our hero take?"
            )
        elif "TASK: end" in prompt:
            text = (
                f"Because the {hero} chose to {choice or 'be brave'}, the last door swung open. "
                f"Friends from all over the {world} cheered, and the glowing map folded itself into a star. "
                "And from that day on, everyone knew that kindness and courage can light any path. The end."
            )
        else:
            text = (
                f"The {hero} decided to {choice or 'keep going'}. "
                "Soon a tiny dragon with a hiccup blocked the way, puffing little clouds of glitter. "
                "Should our hero help the dragon cure its hiccups, or sneak past while it naps?"
            )
        for word in text.split(" "):
            if self.delay:
                time.sleep(self.delay)
            yield word + " "


class MockNarrator:
    """Produces a short two-note WAV chime instead of real speech."""

    name = "mock"
    mimetype = "audio/wav"
    extension = "wav"

    def narrate(self, text: str) -> bytes:
        rate = 16000
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            frames = bytearray()
            for freq in (660, 880):
                for i in range(int(rate * 0.35)):
                    env = min(1.0, i / 400) * max(0.0, 1 - i / (rate * 0.35))
                    frames += struct.pack("<h", int(9000 * env * math.sin(2 * math.pi * freq * i / rate)))
            w.writeframes(bytes(frames))
        return buf.getvalue()


def _between(text: str, start: str, end: str) -> str:
    i = text.find(start)
    if i < 0:
        return ""
    i += len(start)
    j = text.find(end, i)
    return text[i : j if j >= 0 else None].strip()
