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


def _compiles(code: str) -> bool:
    """Check whether a string is valid Python."""
    try:
        compile(code, "<extract>", "exec")
        return True
    except SyntaxError:
        return False


def extract_code(response: str) -> str:
    """Extract Python code from a model response.

    Models return code in many formats:
      - Clean code with no fences (ideal)
      - ```python ... ``` fenced blocks (common)
      - ``` ... ``` fenced blocks without language tag
      - Multiple fenced blocks with prose between them
      - Code with only an opening or only a closing fence
      - Code preceded/followed by prose explanation

    Strategy: try the cheapest extraction first, validate with compile(),
    and fall back progressively to more aggressive cleaning.
    """
    text = response.strip()

    # Step 1: If the raw response already compiles, return it as-is.
    if _compiles(text):
        return text

    # Step 2: Try to extract fenced code blocks.
    fenced = re.findall(
        r"```(?:python|py)?\s*\n(.*?)```",
        text,
        re.DOTALL,
    )
    if fenced:
        code = "\n\n".join(block.strip() for block in fenced)
        if _compiles(code):
            return code

    # Step 3: Strip orphan fence markers (``` without a matching pair).
    lines = text.split("\n")
    cleaned = [
        line for line in lines
        if not re.match(r"^\s*```(?:python|py)?\s*$", line.strip())
    ]
    code = "\n".join(cleaned).strip()
    if _compiles(code):
        return code

    # Step 4: Trim leading/trailing prose by finding the largest
    # contiguous block that compiles. Start from the first line that
    # looks like code (import/def/class/@/from) and take everything
    # from there to the end, then shrink from the end if needed.
    first_code_re = re.compile(
        r"^\s*(import |from |def |class |@)"
    )
    for start in range(len(cleaned)):
        if first_code_re.match(cleaned[start]):
            candidate = "\n".join(cleaned[start:]).strip()
            if _compiles(candidate):
                return candidate
            # Try trimming trailing prose lines from the end
            for end in range(len(cleaned) - 1, start, -1):
                candidate = "\n".join(cleaned[start:end + 1]).strip()
                if _compiles(candidate):
                    return candidate
            break  # Found the code start but couldn't make it compile

    # Step 5: Fallback — return fence-stripped text (best effort).
    return code


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
            max_completion_tokens=config.get("max_tokens", 4096),
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
