import asyncio

import pytest
from fastapi import HTTPException

from src.core.config import get_settings
from src.core.rate_limit import RateLimiter, prediction_slot


def test_rate_limiter_blocks_after_limit():
    limiter = RateLimiter(window_seconds=60)
    assert limiter.check("ip", 2) is None
    assert limiter.check("ip", 2) is None
    retry = limiter.check("ip", 2)
    assert retry is not None and retry >= 1
    # Other clients are unaffected
    assert limiter.check("other-ip", 2) is None


def test_rate_limiter_disabled_with_zero_limit():
    limiter = RateLimiter()
    for _ in range(50):
        assert limiter.check("ip", 0) is None


def test_prediction_slot_returns_503_when_busy():
    settings = get_settings()
    orig = (settings.MAX_CONCURRENT_PREDICTIONS, settings.PREDICTION_QUEUE_TIMEOUT_SECONDS)
    settings.MAX_CONCURRENT_PREDICTIONS, settings.PREDICTION_QUEUE_TIMEOUT_SECONDS = 1, 0.05

    async def scenario():
        async with prediction_slot():
            with pytest.raises(HTTPException) as exc:
                async with prediction_slot():
                    pass
            assert exc.value.status_code == 503
        # Slot is free again afterwards
        async with prediction_slot():
            pass

    try:
        asyncio.run(scenario())
    finally:
        settings.MAX_CONCURRENT_PREDICTIONS, settings.PREDICTION_QUEUE_TIMEOUT_SECONDS = orig
        import src.core.rate_limit as rl
        rl._semaphore = None
