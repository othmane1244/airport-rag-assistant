"""Send a short live request to each configured LLM provider."""

from __future__ import annotations

import sys
import argparse
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402
from app.llm import gemini_client, groq_client  # noqa: E402


PROMPT = "Réponds uniquement avec le mot OK. Ceci est un test de connexion."


def _redact_secrets(message: str) -> str:
    for secret in (settings.gemini_api_key, settings.groq_api_key):
        if secret:
            message = message.replace(secret, "[clé masquée]")
    return message


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--list-groq-models",
        action="store_true",
        help="List model IDs visible to the configured Groq key without generating text.",
    )
    args = parser.parse_args()

    if args.list_groq_models:
        if not settings.groq_api_key:
            print("Groq: NON CONFIGURÉ (clé absente)")
            return 1
        try:
            response = requests.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                timeout=15,
            )
            response.raise_for_status()
            models = response.json().get("data", [])
        except (requests.RequestException, ValueError) as exc:
            print(f"Groq: ÉCHEC — {_redact_secrets(str(exc))[:500]}")
            return 1
        for model in models:
            print(model.get("id", "(id absent)"))
        return 0

    providers = (
        ("Gemini", settings.gemini_api_key, gemini_client.generate),
        ("Groq", settings.groq_api_key, groq_client.generate),
    )
    failures = 0

    for name, key, generate in providers:
        if not key:
            print(f"{name}: NON CONFIGURÉ (clé absente)")
            failures += 1
            continue

        try:
            reply = generate(PROMPT, PROMPT)
        except Exception as exc:  # Report provider HTTP/network errors for diagnosis.
            print(f"{name}: ÉCHEC — {_redact_secrets(str(exc))[:500]}")
            failures += 1
        else:
            safe_reply = _redact_secrets(reply).replace("\r", " ").replace("\n", " ")
            print(f"{name}: OK — {safe_reply[:300]}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
