"""Groq fallback client using the currently available GPT-OSS 120B model."""

import requests

from app.config import settings

BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-120b"


class ConnectorNotConfiguredError(Exception):
    """Clé API manquante dans .env."""


class ConnectorAPIError(Exception):
    """L'API a répondu une erreur, ou une réponse dans un format inattendu."""


def generate(system_prompt: str, user_message: str, context: str = "") -> str:
    if not settings.groq_api_key:
        raise ConnectorNotConfiguredError(
            "GROQ_API_KEY manquante dans .env — voir .env.example"
        )

    user_content = f"{context}\n\nQuestion de l'utilisateur : {user_message}" if context else user_message

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.3,
        "max_tokens": 800,
    }
    headers = {"Authorization": f"Bearer {settings.groq_api_key}"}

    try:
        response = requests.post(BASE_URL, json=payload, headers=headers, timeout=15)
    except requests.RequestException as exc:
        raise ConnectorAPIError("Groq is unreachable") from exc

    if response.status_code != 200:
        raise ConnectorAPIError(f"Groq a répondu {response.status_code} : {response.text[:200]}")

    data = response.json()
    try:
        choice = data["choices"][0]
        if choice.get("finish_reason") == "length":
            raise ConnectorAPIError("Groq response was truncated at the output token limit")
        return choice["message"]["content"]
    except (KeyError, IndexError) as e:
        raise ConnectorAPIError(f"Réponse Groq dans un format inattendu : {data}") from e
