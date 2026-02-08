"""
API Rate Limiting and Protection Utilities.
API 호출 제한 및 보호 유틸리티

yfinance, FRED 등 외부 API 호출 시 과다 호출로 인한 ban 방지
"""
import time
import random
import threading
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable, Any
from functools import wraps
from collections import deque

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter for API calls.
    Thread-safe rate limiting with configurable limits.
    
    분당/일당 호출 제한 및 호출 간 최소 대기 시간 적용
    """
    
    def __init__(
        self,
        calls_per_minute: int = 60,
        calls_per_day: int = 10000,
        min_interval_seconds: float = 0.5,
        name: str = "API"
    ):
        """
        Initialize rate limiter.
        
        Args:
            calls_per_minute: Maximum calls allowed per minute
            calls_per_day: Maximum calls allowed per day
            min_interval_seconds: Minimum seconds between calls
            name: Name for logging purposes
        """
        self.calls_per_minute = calls_per_minute
        self.calls_per_day = calls_per_day
        self.min_interval_seconds = min_interval_seconds
        self.name = name
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Tracking timestamps (using deque for efficient time-window cleanup)
        self._minute_calls: deque = deque()
        self._day_calls: deque = deque()
        self._last_call_time: Optional[float] = None
        
        # Statistics
        self._total_calls = 0
        self._total_waits = 0
        self._total_wait_seconds = 0.0
    
    def acquire(self, timeout: float = 300.0) -> bool:
        """
        Acquire permission to make an API call.
        Blocks until a slot is available or timeout is reached.
        
        Args:
            timeout: Maximum seconds to wait (default: 5 minutes)
            
        Returns:
            True if acquired, False if timeout
        """
        start_time = time.time()
        
        while True:
            with self._lock:
                wait_time = self._calculate_wait_time()
                
                if wait_time <= 0:
                    self._record_call()
                    return True
            
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed + wait_time > timeout:
                logger.warning(
                    f"[{self.name}] Rate limiter timeout after {elapsed:.1f}s"
                )
                return False
            
            # Wait with some jitter to prevent thundering herd
            actual_wait = wait_time + random.uniform(0, 0.1)
            logger.debug(
                f"[{self.name}] Rate limiting: waiting {actual_wait:.2f}s"
            )
            self._total_waits += 1
            self._total_wait_seconds += actual_wait
            time.sleep(actual_wait)
    
    def _calculate_wait_time(self) -> float:
        """Calculate how long to wait before next call is allowed."""
        now = time.time()
        waits = []
        
        # Minimum interval check
        if self._last_call_time is not None:
            elapsed = now - self._last_call_time
            if elapsed < self.min_interval_seconds:
                waits.append(self.min_interval_seconds - elapsed)
        
        # Clean up old timestamps and check limits
        minute_ago = now - 60
        day_ago = now - 86400
        
        # Clean minute window
        while self._minute_calls and self._minute_calls[0] < minute_ago:
            self._minute_calls.popleft()
        
        # Clean day window
        while self._day_calls and self._day_calls[0] < day_ago:
            self._day_calls.popleft()
        
        # Check per-minute limit
        if len(self._minute_calls) >= self.calls_per_minute:
            oldest = self._minute_calls[0]
            waits.append(oldest + 60 - now)
        
        # Check per-day limit
        if len(self._day_calls) >= self.calls_per_day:
            oldest = self._day_calls[0]
            waits.append(oldest + 86400 - now)
        
        return max(waits) if waits else 0.0
    
    def _record_call(self):
        """Record a call timestamp."""
        now = time.time()
        self._minute_calls.append(now)
        self._day_calls.append(now)
        self._last_call_time = now
        self._total_calls += 1
    
    def get_stats(self) -> dict:
        """Get rate limiter statistics."""
        with self._lock:
            now = time.time()
            minute_ago = now - 60
            
            # Count recent calls
            recent_calls = sum(1 for t in self._minute_calls if t > minute_ago)
            
            return {
                "name": self.name,
                "total_calls": self._total_calls,
                "calls_last_minute": recent_calls,
                "calls_today": len(self._day_calls),
                "total_waits": self._total_waits,
                "total_wait_seconds": round(self._total_wait_seconds, 2),
                "limits": {
                    "per_minute": self.calls_per_minute,
                    "per_day": self.calls_per_day,
                    "min_interval": self.min_interval_seconds
                }
            }
    
    def reset(self):
        """Reset all tracking data."""
        with self._lock:
            self._minute_calls.clear()
            self._day_calls.clear()
            self._last_call_time = None
            self._total_calls = 0
            self._total_waits = 0
            self._total_wait_seconds = 0.0


class ExponentialBackoff:
    """
    Exponential backoff handler for API errors.
    지수 백오프 - 연속 오류 시 대기 시간을 지수적으로 증가
    """
    
    def __init__(
        self,
        initial_delay: float = 1.0,
        max_delay: float = 300.0,
        multiplier: float = 2.0,
        max_retries: int = 5,
        jitter: float = 0.1
    ):
        """
        Initialize exponential backoff.
        
        Args:
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay cap in seconds
            multiplier: Delay multiplier (e.g., 2.0 = double each time)
            max_retries: Maximum number of retries
            jitter: Random jitter factor (0.1 = ±10%)
        """
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.max_retries = max_retries
        self.jitter = jitter
        
        self._consecutive_failures = 0
        self._last_failure_time: Optional[float] = None
        self._lock = threading.Lock()
    
    def record_success(self):
        """Record a successful call - resets failure count."""
        with self._lock:
            self._consecutive_failures = 0
    
    def record_failure(self) -> float:
        """
        Record a failed call and return recommended wait time.
        
        Returns:
            Recommended wait time in seconds, or -1 if max retries exceeded
        """
        with self._lock:
            self._consecutive_failures += 1
            self._last_failure_time = time.time()
            
            if self._consecutive_failures > self.max_retries:
                logger.error(
                    f"Max retries ({self.max_retries}) exceeded. "
                    f"Consecutive failures: {self._consecutive_failures}"
                )
                return -1
            
            # Calculate delay with exponential backoff
            delay = self.initial_delay * (
                self.multiplier ** (self._consecutive_failures - 1)
            )
            delay = min(delay, self.max_delay)
            
            # Add jitter
            jitter_amount = delay * self.jitter
            delay += random.uniform(-jitter_amount, jitter_amount)
            
            logger.warning(
                f"API failure #{self._consecutive_failures}. "
                f"Backing off for {delay:.1f}s"
            )
            
            return max(0, delay)
    
    def should_retry(self) -> bool:
        """Check if we should retry after a failure."""
        with self._lock:
            return self._consecutive_failures <= self.max_retries
    
    def get_current_delay(self) -> float:
        """Get current delay without recording a failure."""
        with self._lock:
            if self._consecutive_failures == 0:
                return 0
            
            delay = self.initial_delay * (
                self.multiplier ** (self._consecutive_failures - 1)
            )
            return min(delay, self.max_delay)
    
    def reset(self):
        """Reset backoff state."""
        with self._lock:
            self._consecutive_failures = 0
            self._last_failure_time = None


class ProtectedAPICall:
    """
    Wrapper that combines rate limiting and exponential backoff.
    Rate limiter와 exponential backoff를 결합한 안전한 API 호출 래퍼
    """
    
    def __init__(
        self,
        rate_limiter: RateLimiter,
        backoff: Optional[ExponentialBackoff] = None
    ):
        """
        Initialize protected API call wrapper.
        
        Args:
            rate_limiter: RateLimiter instance
            backoff: ExponentialBackoff instance (created if not provided)
        """
        self.rate_limiter = rate_limiter
        self.backoff = backoff or ExponentialBackoff()
    
    def execute(
        self,
        func: Callable[..., Any],
        *args,
        retry_on_exception: bool = True,
        **kwargs
    ) -> Any:
        """
        Execute a function with rate limiting and retry logic.
        
        Args:
            func: Function to execute
            *args: Arguments to pass to function
            retry_on_exception: Whether to retry on exceptions
            **kwargs: Keyword arguments to pass to function
            
        Returns:
            Function result
            
        Raises:
            RuntimeError: If max retries exceeded or rate limit timeout
        """
        while True:
            # Acquire rate limit slot
            if not self.rate_limiter.acquire():
                raise RuntimeError(
                    f"Rate limit timeout for {self.rate_limiter.name}"
                )
            
            try:
                result = func(*args, **kwargs)
                self.backoff.record_success()
                return result
                
            except Exception as e:
                if not retry_on_exception:
                    raise
                
                # Check for rate limit error (HTTP 429)
                error_str = str(e).lower()
                is_rate_limit = (
                    "429" in error_str or
                    "too many" in error_str or
                    "rate limit" in error_str
                )
                
                if is_rate_limit:
                    # Extra long wait for rate limit errors
                    wait_time = self.backoff.record_failure() * 2
                else:
                    wait_time = self.backoff.record_failure()
                
                if wait_time < 0:
                    raise RuntimeError(
                        f"Max retries exceeded for {self.rate_limiter.name}: {e}"
                    )
                
                time.sleep(wait_time)


# Pre-configured rate limiters for common APIs
def create_fred_limiter() -> RateLimiter:
    """Create rate limiter configured for FRED API."""
    return RateLimiter(
        calls_per_minute=60,      # FRED allows 120/min, we use 50%
        calls_per_day=5000,       # Conservative daily limit
        min_interval_seconds=0.5,
        name="FRED"
    )


def create_yfinance_limiter() -> RateLimiter:
    """Create rate limiter configured for yfinance."""
    return RateLimiter(
        calls_per_minute=30,      # Very conservative - no official limit
        calls_per_day=2000,       # Conservative daily limit
        min_interval_seconds=2.0, # At least 2 seconds between calls
        name="yfinance"
    )
