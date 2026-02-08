"""
Unit tests for rate limiter module.
Rate limiter 모듈 단위 테스트
"""
import time
import threading
import pytest
from loaders.rate_limiter import RateLimiter, ExponentialBackoff, ProtectedAPICall


class TestRateLimiter:
    """Test cases for RateLimiter class."""
    
    def test_basic_acquire(self):
        """Test basic token acquisition."""
        limiter = RateLimiter(calls_per_minute=60, name="TEST")
        
        # First call should succeed immediately
        start = time.time()
        assert limiter.acquire() is True
        elapsed = time.time() - start
        assert elapsed < 1.0  # Should be fast
    
    def test_min_interval_throttling(self):
        """Test minimum interval between calls."""
        limiter = RateLimiter(
            calls_per_minute=100,
            min_interval_seconds=0.5,
            name="TEST"
        )
        
        # First call
        limiter.acquire()
        
        # Second call should wait
        start = time.time()
        limiter.acquire()
        elapsed = time.time() - start
        
        # Should have waited at least min_interval (with some tolerance)
        assert elapsed >= 0.4
    
    def test_per_minute_limit(self):
        """Test per-minute rate limiting."""
        limiter = RateLimiter(
            calls_per_minute=3,
            min_interval_seconds=0.0,
            name="TEST"
        )
        
        # Make 3 calls quickly
        for _ in range(3):
            limiter.acquire()
        
        # 4th call should trigger waiting
        start = time.time()
        limiter.acquire(timeout=5.0)
        elapsed = time.time() - start
        
        # Should have waited (at least some time)
        assert elapsed > 0.0
    
    def test_stats(self):
        """Test statistics tracking."""
        limiter = RateLimiter(calls_per_minute=60, name="TEST")
        
        initial_stats = limiter.get_stats()
        assert initial_stats['total_calls'] == 0
        
        limiter.acquire()
        
        stats = limiter.get_stats()
        assert stats['total_calls'] == 1
        assert stats['calls_last_minute'] == 1
        assert stats['name'] == 'TEST'
    
    def test_reset(self):
        """Test reset functionality."""
        limiter = RateLimiter(calls_per_minute=60, name="TEST")
        limiter.acquire()
        limiter.acquire()
        
        assert limiter.get_stats()['total_calls'] == 2
        
        limiter.reset()
        
        assert limiter.get_stats()['total_calls'] == 0


class TestExponentialBackoff:
    """Test cases for ExponentialBackoff class."""
    
    def test_initial_delay(self):
        """Test initial delay on first failure."""
        backoff = ExponentialBackoff(
            initial_delay=1.0,
            multiplier=2.0
        )
        
        delay = backoff.record_failure()
        assert 0.9 <= delay <= 1.1  # Allow for jitter
    
    def test_exponential_increase(self):
        """Test exponential delay increase."""
        backoff = ExponentialBackoff(
            initial_delay=1.0,
            multiplier=2.0,
            jitter=0.0  # Disable jitter for predictable test
        )
        
        delay1 = backoff.record_failure()  # 1.0
        delay2 = backoff.record_failure()  # 2.0
        delay3 = backoff.record_failure()  # 4.0
        
        assert delay1 == 1.0
        assert delay2 == 2.0
        assert delay3 == 4.0
    
    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        backoff = ExponentialBackoff(
            initial_delay=100.0,
            max_delay=50.0,
            jitter=0.0
        )
        
        delay = backoff.record_failure()
        assert delay == 50.0  # Should be capped
    
    def test_success_resets(self):
        """Test that success resets failure count."""
        backoff = ExponentialBackoff(
            initial_delay=1.0,
            multiplier=2.0,
            jitter=0.0
        )
        
        backoff.record_failure()  # 1.0
        backoff.record_failure()  # 2.0
        
        backoff.record_success()
        
        # Next failure should start over
        delay = backoff.record_failure()
        assert delay == 1.0
    
    def test_max_retries(self):
        """Test max retries limit."""
        backoff = ExponentialBackoff(max_retries=2)
        
        backoff.record_failure()  # 1
        backoff.record_failure()  # 2
        delay = backoff.record_failure()  # 3 - exceeds limit
        
        assert delay == -1  # Indicates max retries exceeded
        assert backoff.should_retry() is False


class TestProtectedAPICall:
    """Test cases for ProtectedAPICall wrapper."""
    
    def test_successful_call(self):
        """Test successful API call execution."""
        limiter = RateLimiter(calls_per_minute=60, name="TEST")
        protected = ProtectedAPICall(limiter)
        
        def mock_api():
            return "success"
        
        result = protected.execute(mock_api)
        assert result == "success"
    
    def test_call_with_arguments(self):
        """Test API call with arguments."""
        limiter = RateLimiter(calls_per_minute=60, name="TEST")
        protected = ProtectedAPICall(limiter)
        
        def mock_api(x, y=10):
            return x + y
        
        result = protected.execute(mock_api, 5, y=15)
        assert result == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
