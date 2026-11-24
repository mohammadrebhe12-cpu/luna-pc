"""العقل الذكي: Ollama (مفتوح المصدر ويعمل محليًا ومجانًا) لفهم الأوامر المعقدة والمحادثة."""
from __future__ import annotations

import datetime as _dt
import json
import logging
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from .actions import ACTION_HELP, ACTION_NAMES
from .config import Config

log = logging.getLogger(__name__)


@dataclass
class LLMReply:
    reply: str = ""
    action: str | None = None
    args: dict = field(default_factory=dict)


def build_system_prompt(honorific: str = "سيدي") -> str:
    actions = "\n".join(f"- {k}: {v}" for k, v in ACTION_HELP.items())
    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""You are "Luna" (لونا), a female assistant inside the app "العمد PC", a polite, witty and efficient voice assistant living on the user's Windows 11 PC (like JARVIS from Iron Man).
Current date/time: {now}. Speak as a woman (in Arabic use feminine first-person forms like "جاهزة", "فتحتُ"). Address the user as "{honorific}" occasionally (in English: "sir").

LANGUAGE: reply in the SAME language the user used. For Arabic, use natural Jordanian/Levantine colloquial Arabic (e.g. هسا، شو، بدك، تمام، كيفك) mixed with simple Modern Standard where needed. Never transliterate Arabic into Latin letters.
STYLE: your reply is spoken aloud, so keep it to 1-3 short sentences, no markdown, no emojis, no lists, no URLs.

OUTPUT: respond with ONE JSON object only, exactly this shape:
{{"reply": "<what to say>", "action": null, "args": {{}}}}
If the user asks you to DO something on the computer, set "action" to one of the names below and fill "args"; keep "reply" as a short confirmation.
If it is just a question or chat, leave "action" null and put the answer in "reply".
Never invent actions that are not listed. For shutdown/restart/sleep still use the action (the app will ask the user to confirm).

AVAILABLE ACTIONS:
{actions}
"""


def parse_llm_output(text: str) -> LLMReply:
    """يحلّل ناتج النموذج؛ يتسامح مع النص الحر أو JSON ملفوف بنص."""
    text = (text or "").strip()
    data = None
    for cand in (text, *re.findall(r"\{.*\}", text, flags=re.S)):
        try:
            data = json.loads(cand)
            break
        except Exception:
            continue
    if not isinstance(data, dict):
        return LLMReply(reply=text)
    action = data.get("action")
    if not isinstance(action, str) or action not in ACTION_NAMES:
        action = None
    args = data.get("args")
    if not isinstance(args, dict):
        args = {}
    reply = data.get("reply")
    return LLMReply(reply=str(reply).strip() if reply else "", action=action, args=args)


class LLMClient:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._avail = (0.0, False)

    @property
    def base(self) -> str:
        return self.cfg.llm_url.rstrip("/")

    def _http(self, path: str, payload: dict | None = None, timeout: float = 5.0) -> dict:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(self.base + path, data=data,
                                     headers={"Content-Type": "application/json"},
                                     method="POST" if data is not None else "GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    def models(self) -> list[str]:
        try:
            return [m["name"] for m in self._http("/api/tags", timeout=2.5).get("models", [])]
        except Exception:
            return []

    def available(self, force: bool = False) -> bool:
        ts, ok = self._avail
        if not force and time.monotonic() - ts < (30 if ok else 8):
            return ok
        ok = bool(self.models())
        self._avail = (time.monotonic(), ok)
        return ok

    def resolve_model(self) -> str | None:
        installed = self.models()
        want = self.cfg.llm_model
        if want in installed:
            return want
        for m in installed:
            if m.split(":")[0] == want.split(":")[0]:
                return m
        return installed[0] if installed else None

    def chat(self, history: list[dict], user_text: str) -> LLMReply:
        model = self.resolve_model()
        if not model:
            raise RuntimeError("no ollama model installed")
        msgs = [{"role": "system", "content": build_system_prompt(self.cfg.honorific)}]
        msgs += history[-10:]
        msgs.append({"role": "user", "content": user_text})
        payload = {"model": model, "messages": msgs, "stream": False, "format": "json", "keep_alive": "30m",
                   "options": {"temperature": 0.3, "num_predict": 320}}
        out = self._http("/api/chat", payload, timeout=90)
        return parse_llm_output(out.get("message", {}).get("content", ""))
