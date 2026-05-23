from __future__ import annotations

import base64
import os
from pathlib import Path

from dotenv import load_dotenv


def load_env(repo_root: Path) -> None:
    load_dotenv(repo_root / ".env")


def read_prompt(repo_root: Path, name: str) -> str:
    path = repo_root / "prompts" / name
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def get_provider() -> str:
    provider = os.getenv("RECIPE_LLM_PROVIDER", "openai").lower()
    if provider == "anthropic" and os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    raise RuntimeError("Set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env")


def structure_text_to_yaml(source_text: str, repo_root: Path, extra: str = "") -> str:
    provider = get_provider()
    system = read_prompt(repo_root, "extract-orf.md")
    user = f"{extra}\n\nSource content:\n\n{source_text}" if extra else f"Source content:\n\n{source_text}"

    if provider == "openai":
        from openai import OpenAI

        client = OpenAI()
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0,
        )
        return (resp.choices[0].message.content or "").strip()

    from anthropic import Anthropic

    client = Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user}],
        temperature=0,
    )
    return resp.content[0].text.strip()


def image_to_yaml(image_path: Path, repo_root: Path, recipe_id: str) -> str:
    provider = get_provider()
    system = read_prompt(repo_root, "extract-orf.md")
    suffix = image_path.suffix.lower()
    media = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(suffix, "image/jpeg")
    b64 = base64.standard_b64encode(image_path.read_bytes()).decode("ascii")
    user_text = f"Extract recipe {recipe_id} from this image into strict ORF YAML."

    if provider == "openai":
        from openai import OpenAI

        client = OpenAI()
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text},
                        {"type": "image_url", "image_url": {"url": f"data:{media};base64,{b64}"}},
                    ],
                },
            ],
            temperature=0,
        )
        return (resp.choices[0].message.content or "").strip()

    from anthropic import Anthropic

    client = Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=system,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media,
                            "data": b64,
                        },
                    },
                ],
            }
        ],
        temperature=0,
    )
    return resp.content[0].text.strip()


def strip_yaml_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()
