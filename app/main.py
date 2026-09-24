from app.config import GEMINI_API_KEY
from app.llm.client import ask_llm_structured
from app.models.research import ResearchResult


SYSTEM_INSTRUCTION = """
You are a technical research assistant.

Return accurate and concise information.
"""


def main():
    print("================================")
    print("     AI Research Agent")
    print("================================")

    if not GEMINI_API_KEY:
        print("Gemini API key is missing.")
        return

    question = input("\nResearch topic: ")

    result = ask_llm_structured(
        prompt=question,
        response_model=ResearchResult,
        system_instruction=SYSTEM_INSTRUCTION,
    )

    print("\n--- Research Result ---")
    print(f"\nTopic: {result.topic}")
    print(f"\nSummary: {result.summary}")

    print("\nKey Points:")

    for point in result.key_points:
        print(f"- {point}")


if __name__ == "__main__":
    main()