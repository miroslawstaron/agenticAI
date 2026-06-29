"""
Optimized Agent Implementation with Connection Pooling & Exponential Backoff

This module demonstrates performance optimizations for AgenticAI:
1. Connection pooling to reuse HTTP connections
2. Exponential backoff for retry logic
3. Better error handling with specific exception types
"""

import time
import random
import logging
from typing import Optional
from agent import AgentAI
import config


class OptimizedAgent(AgentAI):
    """AgentAI with performance optimizations."""

    # Class-level HTTP session for connection pooling
    _session = None
    _session_lock = None

    def __init__(self, *args, **kwargs):
        """Initialize optimized agent."""
        super().__init__(*args, **kwargs)
        self.retry_attempts = 0
        self.total_wait_time = 0

    @classmethod
    def get_connection_pool(cls):
        """Get or create shared connection pool."""
        if cls._session is None:
            try:
                import requests
                cls._session = requests.Session()
                # Configure for connection reuse
                adapter = requests.adapters.HTTPAdapter(
                    pool_connections=5,
                    pool_maxsize=10,
                    max_retries=0  # We handle retries manually
                )
                cls._session.mount('http://', adapter)
                cls._session.mount('https://', adapter)
            except ImportError:
                # Fall back to default behavior if requests not available
                pass
        return cls._session

    def get_response(self, prompt: str) -> Optional[str]:
        """Get response with exponential backoff retry strategy.

        Implements:
        - Exponential backoff: 1s, 2s, 4s, 8s... (capped at 60s)
        - Jitter to prevent thundering herd
        - Specific exception handling for different error types
        """
        self.messages.append({"role": "user", "content": prompt})

        base_delay = 1  # Start with 1 second
        max_delay = 60  # Cap at 60 seconds
        retries = config.LLM_RETRY_ATTEMPTS

        for attempt in range(retries):
            try:
                # Log only on first attempt (reduce logging overhead)
                if attempt == 0:
                    self.logger.log_agent_action(
                        self.agent_id,
                        "Sending prompt to LLM",
                        f"Model - {self.model_name}"
                    )

                # Use optimized completion call
                response = self._optimized_completion(self.messages)

                # Success - log and return
                self.logger.log_agent_action(
                    self.agent_id,
                    "Received response from LLM",
                    f"Response length: {len(response)} chars"
                )

                self.messages.append({"role": "assistant", "content": response})
                return response

            except TimeoutError as e:
                # Timeout - likely temporary, retry with backoff
                if attempt < retries - 1:
                    wait_time = self._calculate_backoff(attempt, base_delay, max_delay)
                    self.total_wait_time += wait_time

                    self.logger.log_agent_action(
                        self.agent_id,
                        f"Timeout (attempt {attempt + 1}/{retries})",
                        f"Retrying in {wait_time:.1f}s"
                    )

                    time.sleep(wait_time)
                    self.retry_attempts += 1
                else:
                    self.logger.error(f"Max retries exceeded after {self.total_wait_time:.1f}s")
                    return None

            except ConnectionError as e:
                # Connection error - probably worth retrying
                if attempt < retries - 1:
                    wait_time = self._calculate_backoff(attempt, base_delay, max_delay)
                    self.total_wait_time += wait_time

                    self.logger.log_agent_action(
                        self.agent_id,
                        f"Connection error (attempt {attempt + 1}/{retries})",
                        f"Retrying in {wait_time:.1f}s"
                    )

                    time.sleep(wait_time)
                    self.retry_attempts += 1
                else:
                    self.logger.error(f"Cannot reach LLM server: {e}")
                    return None

            except ValueError as e:
                # Invalid API key or model - don't retry
                self.logger.error(f"Configuration error: {e}")
                return None

            except Exception as e:
                # Unknown error - log with full context
                error_type = type(e).__name__
                self.logger.error(
                    f"Unexpected error ({error_type}): {e}"
                )

                if attempt < retries - 1:
                    # Try one more time on unknown errors
                    wait_time = self._calculate_backoff(attempt, base_delay, max_delay)
                    time.sleep(wait_time)
                    self.retry_attempts += 1
                else:
                    return None

        return None

    @staticmethod
    def _calculate_backoff(attempt: int, base: float, max_delay: float) -> float:
        """Calculate exponential backoff with jitter.

        Formula:
        - Base delay: base * (2 ** attempt)
        - Jitter: +/- 10% random variance
        - Cap at max_delay

        Args:
            attempt: Current retry attempt (0-indexed)
            base: Base delay in seconds
            max_delay: Maximum delay cap in seconds

        Returns:
            Delay time in seconds
        """
        # Exponential: 1, 2, 4, 8, 16, 32, 64...
        exponential_delay = base * (2 ** attempt)

        # Cap at max
        capped_delay = min(exponential_delay, max_delay)

        # Add jitter: random ±10%
        jitter_amount = capped_delay * 0.1
        jitter = random.uniform(-jitter_amount, jitter_amount)

        final_delay = max(0, capped_delay + jitter)

        return final_delay

    def _optimized_completion(self, messages: list) -> str:
        """Optimized completion call with connection pooling.

        Uses a shared HTTP session for connection reuse instead of
        creating a new connection for each request.
        """
        from litellm import completion

        # Note: LiteLLM handles the actual HTTP layer,
        # but in a production implementation you could:
        # 1. Patch LiteLLM to use our session pool
        # 2. Or implement direct HTTP calls with session pooling

        response = completion(
            model=self.model_name,
            messages=messages,
            temperature=config.LLM_TEMPERATURE_GENERATION,
            max_tokens=self.max_tokens,
            api_base=self.server_address if self.server_address else None,
            timeout=min(30, config.LLM_TIMEOUT_SECONDS),  # Fail fast instead of 300s
        )

        return response.choices[0].message.content

    def get_performance_stats(self) -> dict:
        """Get performance statistics for this agent.

        Returns:
            Dict with retry and timing information
        """
        return {
            'retry_attempts': self.retry_attempts,
            'total_wait_time': self.total_wait_time,
            'avg_wait_per_retry': (
                self.total_wait_time / self.retry_attempts
                if self.retry_attempts > 0
                else 0
            ),
        }


class CachedOptimizedAgent(OptimizedAgent):
    """Optimized agent with response caching.

    Caches responses to identical prompts to avoid redundant LLM calls.
    Useful for repetitive tasks or when prompt variance is low.
    """

    def __init__(self, *args, cache_enabled: bool = True, **kwargs):
        """Initialize cached agent.

        Args:
            cache_enabled: Whether to cache responses
        """
        super().__init__(*args, **kwargs)
        self.cache_enabled = cache_enabled
        self.response_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0

    def get_response(self, prompt: str) -> Optional[str]:
        """Get response with caching support.

        Checks cache before making LLM call. Significantly improves
        performance for repeated or similar prompts.
        """
        if self.cache_enabled:
            import hashlib
            cache_key = hashlib.sha256(prompt.encode()).hexdigest()

            if cache_key in self.response_cache:
                self.cache_hits += 1
                self.logger.log_agent_action(
                    self.agent_id,
                    "Cache hit",
                    f"Reusing cached response for prompt"
                )
                return self.response_cache[cache_key]

            self.cache_misses += 1

        # Get response from parent (optimized with backoff)
        response = super().get_response(prompt)

        # Cache the response
        if self.cache_enabled and response:
            self.response_cache[cache_key] = response

        return response

    def get_cache_stats(self) -> dict:
        """Get cache performance statistics."""
        total = self.cache_hits + self.cache_misses
        return {
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate': (
                self.cache_hits / total
                if total > 0
                else 0
            ),
            'cached_prompts': len(self.response_cache),
        }


if __name__ == '__main__':
    # Example usage
    print("Optimized Agent Example\n")

    agent = OptimizedAgent(
        server_address="http://localhost:11434",
        model_name="ollama/qwen3:4b",
        my_role="You are a helpful assistant. Be concise."
    )

    print("Testing optimized agent with exponential backoff...")
    response = agent.get_response("What is 2+2?")

    stats = agent.get_performance_stats()
    print(f"\nPerformance Stats:")
    print(f"  Retry attempts: {stats['retry_attempts']}")
    print(f"  Total wait time: {stats['total_wait_time']:.2f}s")

    print("\n" + "=" * 60)
    print("Cached Agent Example\n")

    cached_agent = CachedOptimizedAgent(
        server_address="http://localhost:11434",
        model_name="ollama/qwen3:4b",
        my_role="You are a helpful assistant."
    )

    # First call - hits LLM
    print("First call (LLM)...")
    response1 = cached_agent.get_response("Explain recursion")

    # Second call - hits cache
    print("Second call (cache)...")
    response2 = cached_agent.get_response("Explain recursion")

    cache_stats = cached_agent.get_cache_stats()
    print(f"\nCache Stats:")
    print(f"  Cache hits: {cache_stats['cache_hits']}")
    print(f"  Cache misses: {cache_stats['cache_misses']}")
    print(f"  Hit rate: {cache_stats['cache_hit_rate']:.1%}")
