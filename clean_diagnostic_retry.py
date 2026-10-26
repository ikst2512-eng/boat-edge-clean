"""Bounded, testable retry for diagnostic HTTP fetches only."""
from urllib.error import URLError
import time

def fetch_with_retry(request, opener, *, attempts=2, timeout=10, sleep=time.sleep):
    if not isinstance(attempts, int) or not 1 <= attempts <= 3:
        raise ValueError("invalid attempt limit")
    for number in range(1, attempts + 1):
        try:
            with opener(request, timeout=timeout) as response:
                if response.status != 200:
                    raise ValueError("unexpected HTTP status")
                payload = response.read(2_000_001)
            if not payload or len(payload) > 2_000_000:
                raise ValueError("invalid payload size")
            return payload, number
        except (TimeoutError, URLError):
            if number == attempts:
                raise
            sleep(1)
    raise AssertionError("unreachable")
