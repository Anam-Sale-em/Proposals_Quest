"""Load config.toml and secrets. Secrets come from the environment (.env) or st.secrets."""
from __future__ import annotations

import os
import tomllib
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@lru_cache(maxsize=1)
def load_config() -> dict:
    path = Path(os.environ.get("PV2_CONFIG", ROOT / "config.toml"))
    with open(path, "rb") as f:
        return tomllib.load(f)


def env_path() -> Path:
    return Path(os.environ.get("PV2_ENV_FILE", ROOT / ".env"))


def save_env(values: dict[str, str]) -> None:
    """Writes or updates keys in .env (used by the in-app setup screen) and applies them now."""
    path = env_path()
    lines = _env_text(path).splitlines() if path.exists() else []
    done = set()
    for i, line in enumerate(lines):
        key = line.split("=", 1)[0].strip()
        if key in values and not line.lstrip().startswith("#"):
            lines[i] = f"{key}={values[key]}"
            done.add(key)
    lines += [f"{k}={v}" for k, v in values.items() if k not in done]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.environ.update(values)


def _env_text(path: Path) -> str:
    raw = path.read_bytes()
    # Windows editors may save with a BOM (Notepad) or as UTF-16 (PowerShell's ">").
    return raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8-sig", errors="replace")


def _load_dotenv() -> None:
    env = env_path()
    if not env.exists():
        return
    for line in _env_text(env).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


def secret(name: str, default: str | None = None) -> str | None:
    """Read a secret from the environment, then from st.secrets when running in Streamlit."""
    value = os.environ.get(name)
    if value:
        return value
    try:
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return default


def prompt_version() -> str:
    return load_config()["prompt_version"]
