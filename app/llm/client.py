from typing import TypeVar

from google import genai
from pydantic import BaseModel

from app.config import GEMINI_API_KEY


client = genai.Client(api_key=GEMINI_API_KEY)

T = TypeVar("T", bound=BaseModel)


def ask_llm(
    prompt: str,
    system_instruction: str | None = None,
) -> str:

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "system_instruction": system_instruction,
            } if system_instruction else None,
        )

        return response.text

    except Exception as error:
        raise RuntimeError(
            f"Gemini request failed: {error}"
        ) from error

from typing import TypeVar

from google import genai
from pydantic import BaseModel

from app.config import GEMINI_API_KEY


client = genai.Client(api_key=GEMINI_API_KEY)

T = TypeVar("T", bound=BaseModel)


def ask_llm_structured(
    prompt: str,
    response_model: type[T],
    system_instruction: str | None = None,
) -> T:

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
            config={
                "system_instruction": system_instruction,
            } if system_instruction else None,
        )

        return response_model(**response.text)

    except Exception as error:
        raise RuntimeError(
            f"Gemini request failed: {error}"
        ) from error