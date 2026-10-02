import os

from dotenv import load_dotenv


load_dotenv()


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

QUERIES_PER_ROUND = int(os.getenv("QUERIES_PER_ROUND", "3"))
RESULTS_PER_QUERY = int(os.getenv("RESULTS_PER_QUERY", "3"))
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "2"))
MAX_SOURCES_PER_ROUND = int(os.getenv("MAX_SOURCES_PER_ROUND", "5"))

LLM_REQUESTS_PER_MINUTE = int(os.getenv("LLM_REQUESTS_PER_MINUTE", "5"))

MAX_PAGE_CHARS = int(os.getenv("MAX_PAGE_CHARS", "12000"))

MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "4"))
