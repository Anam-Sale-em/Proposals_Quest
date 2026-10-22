"""Shows which configured models your keys can actually use. Uses no generation quota.

  python scripts/check_models.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from proposal_v2.config import load_config, secret  # noqa: E402


def main():
    m = load_config()["models"]
    print("Gemini")
    key = secret("GEMINI_API_KEY")
    if not key:
        print("  no GEMINI_API_KEY set")
    else:
        from google import genai
        client = genai.Client(api_key=key)
        for name in (m["draft"], m["light"]):
            try:
                client.models.get(model=name)
                print(f"  OK       {name}")
            except Exception as e:
                print(f"  MISSING  {name}  ({str(e)[:90]})")
    print("Groq")
    key = secret("GROQ_API_KEY")
    if not key:
        print("  no GROQ_API_KEY set")
        return
    import groq
    try:
        available = {x.id for x in groq.Groq(api_key=key).models.list().data}
    except Exception as e:
        print(f"  couldn't list models: {str(e)[:120]}")
        return
    for name in dict.fromkeys(m.get("fallbacks", []) + m.get("judges", [])):
        print(f"  {'OK     ' if name in available else 'MISSING'}  {name}")
    print("\nModels your Groq key can use:", ", ".join(sorted(available)))
    print("Edit [models] in config.toml so fallbacks and judges list only OK models.")


if __name__ == "__main__":
    main()
