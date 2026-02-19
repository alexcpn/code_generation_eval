"""
AI provider abstraction for eval runner.

Supported providers:
  anthropic — Claude models via Anthropic SDK  (pip install anthropic)
  openai    — Any OpenAI-compatible API        (pip install openai)
              This includes: OpenAI, Google Gemini, DeepSeek, Together, etc.
              Set api_base in eval_config.yaml to point to the right endpoint.

Google Gemini OpenAI-compatible endpoint:
  api_base: https://generativelanguage.googleapis.com/v1beta/openai/
  api_key_env: GOOGLE_API_KEY
"""

import os
import re


def extract_code(response: str) -> str:
    """Extract Python code from a model response.

    Models often wrap code in ```python ... ``` blocks or add explanations.
    This extracts just the code.
    """
    # Try to find fenced code blocks (```python ... ``` or ``` ... ```)
    fenced = re.findall(r"```(?:python)?\s*\n(.*?)```", response, re.DOTALL)
    if fenced:
        # If multiple blocks, join them (model may split imports from implementation)
        return "\n\n".join(block.strip() for block in fenced)

    # If no fences, check if the whole response looks like code
    lines = response.strip().split("\n")
    code_lines = [
        l for l in lines
        if not l.startswith("Here") and not l.startswith("This ")
        and not l.startswith("Note:") and not l.startswith("The ")
        and not l.startswith("I ")
    ]
    # If most lines look like code (start with def, class, import, #, whitespace, or are empty)
    code_like = sum(
        1 for l in code_lines
        if re.match(r"^(\s|def |class |import |from |#|@|$)", l)
    )
    if code_like > len(code_lines) * 0.5:
        return "\n".join(code_lines)

    # Fallback: return everything
    return response.strip()


def _resolve_api_key(model_config: dict) -> str:
    """Get API key from env var or config."""
    env_var = model_config.get("api_key_env")
    if env_var:
        key = os.environ.get(env_var)
        if key:
            return key
    key = model_config.get("api_key")
    if key:
        return key
    raise ValueError(
        f"No API key found. Set {env_var} environment variable "
        f"or add api_key to eval_config.yaml"
    )


def send_anthropic(system: str, user: str, config: dict) -> str:
    """Send prompt via Anthropic API."""
    try:
        import anthropic
    except ImportError:
        raise ImportError("pip install anthropic")

    client = anthropic.Anthropic(api_key=_resolve_api_key(config))
    response = client.messages.create(
        model=config["model"],
        max_tokens=config.get("max_tokens", 4096),
        temperature=config.get("temperature", 0.0),
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text


def send_openai(system: str, user: str, config: dict) -> str:
    """Send prompt via OpenAI-compatible API (OpenAI, DeepSeek, etc.)."""
    try:
        import openai
    except ImportError:
        raise ImportError("pip install openai")

    kwargs = {}
    api_base = config.get("api_base")
    if api_base:
        kwargs["base_url"] = api_base

    client = openai.OpenAI(api_key=_resolve_api_key(config), **kwargs)

    model = config["model"]
    is_reasoning = model.startswith("o1") or model.startswith("o3")

    if is_reasoning:
        # o-series models: no system message, use developer message instead
        response = client.chat.completions.create(
            model=model,
            max_completion_tokens=config.get("max_tokens", 16384),
            temperature=config.get("temperature", 1.0),
            messages=[
                {"role": "developer", "content": system},
                {"role": "user", "content": user},
            ],
        )
    else:
        response = client.chat.completions.create(
            model=model,
            max_tokens=config.get("max_tokens", 4096),
            temperature=config.get("temperature", 0.0),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
    return response.choices[0].message.content


# Provider dispatch
PROVIDERS = {
    "anthropic": send_anthropic,
    "openai": send_openai,
}


def send_prompt(system: str, user: str, model_config: dict) -> str:
    """Send a prompt to any configured provider. Returns raw response text."""
    provider = model_config["provider"]
    if provider not in PROVIDERS:
        raise ValueError(
            f"Unknown provider '{provider}'. "
            f"Supported: {', '.join(PROVIDERS.keys())}"
        )
    return PROVIDERS[provider](system, user, model_config)
