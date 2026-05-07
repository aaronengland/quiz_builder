import logging

import httpx

logger = logging.getLogger("quiz_builder")

WIKIPEDIA_API = "https://en.wikipedia.org/api/rest_v1/page/summary"


async def fetch_wikipedia_summary(topic: str) -> str | None:
    """Fetch a Wikipedia summary for the given topic.

    Returns the extract text on success, or None if the lookup fails.
    The quiz generator still works without this context, so failures
    are logged and swallowed rather than raised.
    """
    url = f"{WIKIPEDIA_API}/{topic}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("extract")
    except Exception as exc:
        logger.warning("Wikipedia fetch failed for '%s': %s", topic, exc)
    return None
