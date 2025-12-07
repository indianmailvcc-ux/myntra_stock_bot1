import asyncio
from typing import Literal, Optional

import requests
from bs4 import BeautifulSoup

StockStatus = Literal["in_stock", "out_of_stock", "unknown"]


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/129.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def _parse_stock(html: str, size: str) -> StockStatus:
    """
    Try to detect given size's stock status.
    You may need to adjust CSS selectors if Myntra markup changes.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Common pattern: size buttons
    candidates = soup.select("button, li, div")

    size_lower = size.strip().lower()

    for elem in candidates:
        text = elem.get_text(strip=True).lower()
        if text == size_lower:
            classes = " ".join(elem.get("class") or []).lower()

            disabled = (
                "disabled" in classes
                or "out-of-stock" in classes
                or "oos" in classes
            )

            # if data-size or any data-* attribute has hints, check here too later

            if disabled:
                return "out_of_stock"
            else:
                return "in_stock"

    # If size not found clearly
    return "unknown"


def _sync_check_stock(url: str, size: str) -> StockStatus:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return "unknown"
        return _parse_stock(resp.text, size)
    except Exception:
        return "unknown"


async def check_stock(url: str, size: str) -> StockStatus:
    """
    Async wrapper using thread so we don't block event loop.
    """
    return await asyncio.to_thread(_sync_check_stock, url, size) 