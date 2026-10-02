from ddgs import DDGS


def search_web(query: str, max_results: int = 5) -> list[dict]:
    try:
        results = DDGS().text(query, max_results=max_results)
    except Exception as error:
        print(f"  ! search failed for {query!r}: {error}")
        return []

    return [
        {
            "title": result.get("title", ""),
            "url": result.get("href", ""),
            "snippet": result.get("body", ""),
        }
        for result in results
        if result.get("href")
    ]
