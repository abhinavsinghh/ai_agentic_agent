import re
import threading
import time
from typing import TypeVar

from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from app.config import GEMINI_API_KEY, GEMINI_MODEL, LLM_REQUESTS_PER_MINUTE


client = genai.Client(api_key=GEMINI_API_KEY)

NO_AFC = types.AutomaticFunctionCallingConfig(disable=True)

T = TypeVar("T", bound=BaseModel)

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRIES = 4

MAX_RETRY_WAIT_SECONDS = 90


class _RateLimiter:
    def __init__(self, requests_per_minute: int):
        self.interval = 60 / requests_per_minute if requests_per_minute > 0 else 0
        self.next_slot = 0.0
        self.lock = threading.Lock()

    def wait(self):
        with self.lock:
            now = time.monotonic()
            slot = max(now, self.next_slot)
            self.next_slot = slot + self.interval
        time.sleep(slot - now)


_rate_limiter = _RateLimiter(LLM_REQUESTS_PER_MINUTE)


def _retry_delay(error: errors.APIError, attempt: int) -> float:
    match = re.search(r"retryDelay': '([\d.]+)s'", str(error))
    return float(match.group(1)) + 1 if match else 2 ** (attempt + 1)


def _generate(prompt: str, config: types.GenerateContentConfig) -> types.GenerateContentResponse:
    for attempt in range(MAX_RETRIES + 1):
        _rate_limiter.wait()

        try:
            return client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=config,
            )

        except errors.APIError as error:
            delay = _retry_delay(error, attempt)

            if (
                error.code not in RETRYABLE_STATUS_CODES
                or attempt == MAX_RETRIES
                or delay > MAX_RETRY_WAIT_SECONDS
            ):
                raise RuntimeError(
                    f"Gemini request failed ({error.code} {error.status}): "
                    f"{(error.message or '').split(chr(10))[0]}"
                ) from error

            time.sleep(delay)

    raise AssertionError("unreachable")


def ask_llm(
    prompt: str,
    system_instruction: str | None = None,
) -> str:
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        automatic_function_calling=NO_AFC,
    )

    return _generate(prompt, config).text or ""


def ask_llm_structured(
    prompt: str,
    response_model: type[T],
    system_instruction: str | None = None,
) -> T:
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json",
        response_schema=response_model,
        automatic_function_calling=NO_AFC,
    )

    response = _generate(prompt, config)

    if isinstance(response.parsed, response_model):
        return response.parsed

    try:
        return response_model.model_validate_json(response.text or "")
    except Exception as error:
        raise RuntimeError(
            f"Gemini returned invalid {response_model.__name__} JSON: {error}"
        ) from error
