"""LLM client: Gemini first, Groq when Gemini rate-limits or errors, a response cache,
replay mode and a log line for every call.

Modes
  live         always call a provider; the response is also cached
  cache_first  use a cached response when one exists, otherwise call and cache (evals)
  replay       cached responses only, so demos and evals run the same every time, offline
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import threading
import time
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from .config import ROOT, load_config, prompt_version, secret

T = TypeVar("T", bound=BaseModel)
CACHE_DIR = ROOT / "evals" / "cache"
LOG_DIR = ROOT / "logs" / "runs"


class LLMError(Exception):
    """Shown to the user as written: says what happened and what to do next."""


class ReplayMiss(LLMError):
    pass


@lru_cache(maxsize=1)
def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "no-git"


@dataclass
class CallRecord:
    step: str
    role: str
    provider: str
    model: str
    cached: bool
    latency_s: float
    tokens_in: int = 0
    tokens_out: int = 0
    error: str = ""


@dataclass
class LLM:
    mode: str = "live"
    cache_dir: Path = CACHE_DIR  # where responses are written (and read first)
    read_dirs: list[Path] = field(default_factory=list)  # extra folders read for replay, never written
    log_dir: Optional[Path] = LOG_DIR
    calls: list[CallRecord] = field(default_factory=list)
    _last_call: dict = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    # ------------------------------------------------------------------ public
    def call(self, step: str, role: str, system: str, user: str, schema: Type[T], temperature: float = 0.0) -> T:
        cfg = load_config()
        model = cfg["models"][role]
        key = self._key(role, model, system, user, schema)
        cached = self._read_cache(key, schema)
        if cached is not None and self.mode in ("cache_first", "replay"):
            self._record(CallRecord(step, role, "cache", model, True, 0.0))
            return cached
        if self.mode == "replay":
            raise ReplayMiss(f"Replay mode has no saved response for the {step} step. Run once with LLM_MODE=live or the eval runner with --record.")

        errors = []
        m = cfg["models"]
        waits = list(cfg.get("retries", {}).get("waits_s", [3, 8]))
        if role == "judge":
            providers = [("groq", j, []) for j in m.get("judges", [m.get("judge")]) if j]
        else:
            # A busy model is retried after a short wait, then the other Gemini model, then each Groq fallback.
            other = m["light"] if role != "light" else m["draft"]
            providers = [("gemini", model, waits), ("gemini", other, waits[:1])]
            providers += [("groq", f, []) for f in m.get("fallbacks", [m.get("fallback")]) if f]
        for provider, prov_model, retry_waits in providers:
            busy_retries = list(retry_waits)
            attempt = 0
            while attempt < 2:  # one repair attempt on a schema failure
                t0 = time.time()
                try:
                    self._throttle(prov_model)
                    extra = "" if attempt == 0 else f"\n\nYour last reply didn't match the schema: {errors[-1]}. Reply again with valid JSON only."
                    if provider == "gemini":
                        text, tin, tout = self._gemini(prov_model, system, user + extra, schema, temperature)
                    else:
                        text, tin, tout = self._groq(prov_model, system, user + extra, schema, temperature)
                    obj = schema.model_validate_json(_strip_fences(text))
                    self._record(CallRecord(step, role, provider, prov_model, False, round(time.time() - t0, 2), tin, tout))
                    self._write_cache(key, obj, provider, prov_model, step)
                    return obj
                except ValidationError as e:
                    errors.append(f"{prov_model} schema: {str(e)[:200]}")
                    self._record(CallRecord(step, role, provider, prov_model, False, round(time.time() - t0, 2), error="schema"))
                    attempt += 1
                    continue
                except _Unavailable as e:
                    errors.append(f"{prov_model}: {e}")
                    self._record(CallRecord(step, role, provider, prov_model, False, round(time.time() - t0, 2), error=str(e)[:120]))
                    if e.retryable and busy_retries:
                        time.sleep(busy_retries.pop(0))
                        continue
                    break  # next model
        busy = any(" 503" in x or " 429" in x or "high demand" in x for x in errors)
        lead = ("The AI models are busy right now, and the backups didn't answer either. Wait a minute and try again."
                if busy else "The AI service didn't respond properly after trying every model. Check your Gemini and Groq keys and quotas,"
                " and run `python scripts/check_models.py` to see which models your keys can use.")
        raise LLMError(lead + " Details: " + " | ".join(errors)[-500:])

    def steps_called(self) -> list[str]:
        return [c.step for c in self.calls if not c.error]

    # ------------------------------------------------------------------ providers
    def _gemini(self, model, system, user, schema, temperature):
        key = secret("GEMINI_API_KEY")
        if not key:
            raise _Unavailable("no GEMINI_API_KEY")
        from google import genai
        from google.genai import errors as gerrors
        from google.genai import types

        client = genai.Client(api_key=key)
        try:
            resp = client.models.generate_content(
                model=model,
                contents=user,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=temperature,
                ),
            )
        except gerrors.APIError as e:
            code = getattr(e, "code", 0) or 0
            raise _Unavailable(f"gemini {code}: {str(e)[:160]}", retryable=code in (429, 500, 502, 503, 504))
        except Exception as e:  # network and SDK errors
            raise _Unavailable(f"gemini: {str(e)[:160]}", retryable=True)
        usage = resp.usage_metadata
        return resp.text or "", getattr(usage, "prompt_token_count", 0) or 0, getattr(usage, "candidates_token_count", 0) or 0

    def _groq(self, model, system, user, schema, temperature):
        key = secret("GROQ_API_KEY")
        if not key:
            raise _Unavailable("no GROQ_API_KEY")
        import groq

        client = groq.Groq(api_key=key)
        sys = system + "\n\nReply with one JSON object only, matching this JSON schema:\n" + json.dumps(schema.model_json_schema())
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": sys}, {"role": "user", "content": user}],
                response_format={"type": "json_object"},
                temperature=temperature,
            )
        except (groq.RateLimitError, groq.InternalServerError, groq.APIConnectionError) as e:
            raise _Unavailable(f"groq: {str(e)[:160]}", retryable=True)
        except groq.APIError as e:
            raise _Unavailable(f"groq: {str(e)[:160]}")
        except Exception as e:
            raise _Unavailable(f"groq: {str(e)[:160]}")
        u = resp.usage
        return resp.choices[0].message.content or "", getattr(u, "prompt_tokens", 0) or 0, getattr(u, "completion_tokens", 0) or 0

    # ------------------------------------------------------------------ plumbing
    def _throttle(self, model: str) -> None:
        rpm = load_config().get("rate_limits", {}).get(model)
        if not rpm:
            return
        gap = 60.0 / float(rpm)
        with self._lock:
            last = self._last_call.get(model, 0.0)
            wait = last + gap - time.time()
            if wait > 0:
                time.sleep(wait)
            self._last_call[model] = time.time()

    def _key(self, role, model, system, user, schema) -> str:
        blob = json.dumps({"v": prompt_version(), "role": role, "model": model, "system": system,
                           "user": user, "schema": schema.__name__}, sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()[:24]

    def _read_cache(self, key: str, schema: Type[T]) -> Optional[T]:
        for folder in [self.cache_dir, *self.read_dirs]:
            path = folder / f"{key}.json"
            if not path.exists():
                continue
            try:
                return schema.model_validate(json.loads(path.read_text(encoding="utf-8"))["response"])
            except Exception:
                continue
        return None

    def _write_cache(self, key, obj: BaseModel, provider, model, step) -> None:
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            (self.cache_dir / f"{key}.json").write_text(json.dumps(
                {"step": step, "provider": provider, "model": model, "prompt_version": prompt_version(),
                 "response": obj.model_dump(mode="json")}, indent=1), encoding="utf-8")
        except OSError:
            pass

    def _record(self, rec: CallRecord) -> None:
        self.calls.append(rec)
        if not self.log_dir:
            return
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            line = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "prompt_version": prompt_version(), "commit": git_commit(),
                    "mode": self.mode, **rec.__dict__}
            with open(self.log_dir / f"{time.strftime('%Y-%m-%d')}.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(line) + "\n")
        except OSError:
            pass


class _Unavailable(Exception):
    def __init__(self, msg: str, retryable: bool = False):
        super().__init__(msg)
        self.retryable = retryable


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        t = t.rsplit("```", 1)[0]
    return t.strip()


def make_llm(mode: Optional[str] = None) -> LLM:
    """The app's LLM. Its responses hold users' jobs and drafts, so they're cached in the
    gitignored data folder, never in evals/cache (which is committed). Replay mode can still
    read evals/cache, where the eval runner saves the sample jobs' responses for demos."""
    data_root = Path(secret("PV2_DATA_ROOT") or (ROOT / load_config()["storage"]["json_root"]))
    return LLM(mode=mode or secret("LLM_MODE", "live"), cache_dir=data_root / "llm_cache", read_dirs=[CACHE_DIR])
