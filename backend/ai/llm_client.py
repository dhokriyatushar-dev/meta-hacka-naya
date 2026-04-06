"""
=============================================================================
Meta Hackathon Submission: EduPath AI
=============================================================================
This file is part of the EduPath AI core architecture. 
It strictly adheres to the OpenEnv reinforcement learning specification.
Architecture Layer: Backend Logic & State Management
Design Pattern: Highly modularized, utilizing Pydantic for rigid type safety,
and designed for deterministic, reproducible inference evaluation.
=============================================================================
"""
"""
import os
import json
import logging

logger = logging.getLogger(__name__)


def _get_config():
    """Get LLM configuration from environment variables."""
    api_base_url = os.getenv("API_BASE_URL")
    model_name = os.getenv("MODEL_NAME", "gpt-4o-mini")
    hf_token = os.getenv("HF_TOKEN", "")

    if not api_base_url:
        raise ValueError(
            "API_BASE_URL environment variable not set. "
            "Set it to your LLM endpoint (e.g. https://api.openai.com/v1)"
        )
    return api_base_url, model_name, hf_token


def _get_client():
    """Get OpenAI-compatible client."""
    from openai import OpenAI

    api_base_url, model_name, hf_token = _get_config()

    # Use HF_TOKEN as the API key (works for HuggingFace endpoints too)
    api_key = hf_token or os.getenv("OPENAI_API_KEY", "sk-placeholder")

    client = OpenAI(
        base_url=api_base_url,
        api_key=api_key,
    )
    return client, model_name


def generate_json(system_prompt: str, user_prompt: str) -> dict:
    """Generate structured JSON output from LLM using OpenAI client."""
    client, model_name = _get_client()

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            top_p=0.9,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        if not raw or raw.strip() == "":
            logger.error("LLM returned empty response")
            return {}
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"LLM returned invalid JSON: {e}")
        return {}
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        raise


def generate_text(system_prompt: str, user_prompt: str) -> str:
    """Generate free-text output from LLM using OpenAI client."""
    client, model_name = _get_client()

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,
            top_p=0.9,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        logger.error(f"LLM text generation failed: {e}")
        raise


def is_api_key_set() -> bool:
    """Check if the required LLM environment variables are configured."""
    return bool(os.getenv("API_BASE_URL"))
