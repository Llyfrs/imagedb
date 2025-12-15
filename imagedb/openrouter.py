from __future__ import annotations

import base64
import json
from typing import List

import requests

EMBEDDING_MODEL = "qwen/qwen3-embedding-8b"
CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
EMBED_URL = "https://openrouter.ai/api/v1/embeddings"
VISION_PROMPT = (
    "Describe the image in detail. If there is any text present, fully transcribe it. Do not use any formating, keep it short (1-3 paragraphs)."
)


def _headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def describe_image(
    image_bytes: bytes, api_key: str, model: str, context: str | None = None
) -> str:
    """
    Call OpenRouter vision model to get a description of the image.
    """
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    prompt = (
        f"{VISION_PROMPT} Additional context: {context}"
        if context
        else VISION_PROMPT
    )
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                ],
            }
        ],
    }

    resp = requests.post(CHAT_URL, headers=_headers(api_key), data=json.dumps(payload))
    if resp.status_code != 200:
        raise RuntimeError(
            f"Vision API error {resp.status_code}: {resp.text[:200]}"
        )
    data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("Vision API returned no choices.")

    content = choices[0]["message"]["content"]
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        texts = [part.get("text", "") for part in content if part.get("type") == "text"]
        return " ".join(t.strip() for t in texts if t).strip()

    raise RuntimeError("Unexpected vision response format.")


def get_embedding(text: str, api_key: str) -> List[float]:
    """
    Fetch an embedding vector for the provided text.
    """
    payload = {
        "model": EMBEDDING_MODEL,
        "input": text,
        "encoding_format": "float",
    }
    resp = requests.post(EMBED_URL, headers=_headers(api_key), data=json.dumps(payload))
    if resp.status_code != 200:
        raise RuntimeError(
            f"Embedding API error {resp.status_code}: {resp.text[:200]}"
        )
    data = resp.json()
    embed_list = data.get("data", [])
    if not embed_list:
        raise RuntimeError("Embedding API returned no data.")
    embedding = embed_list[0].get("embedding")
    if not embedding:
        raise RuntimeError("Embedding missing in response.")
    return embedding

