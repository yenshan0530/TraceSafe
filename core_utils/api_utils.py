import time
import os
from colorama import Fore
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

# We wrap API network exceptions directly to guarantee robust retry strategies
# This ensures 429 Rate Limits and Timeout interruptions do not hard-fail the threading.
def log_retry_attempt(retry_state):
    print(f"{Fore.YELLOW}API request failed (Attempt {retry_state.attempt_number}). Retrying in {retry_state.next_action.sleep}s...{Fore.RESET}")
    print(f"{Fore.RED}Exception: {retry_state.outcome.exception()}{Fore.RESET}")

api_retry = retry(
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(5),
    reraise=True,
    before_sleep=log_retry_attempt
)
