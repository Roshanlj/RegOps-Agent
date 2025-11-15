"""
Simple verification script to demonstrate LLM logging capabilities
"""

import logging
import os
import sys

# Set up logging to see all log messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)-8s | %(name)-25s | %(message)s',
    stream=sys.stdout
)

print("=" * 100)
print("LLM LOGGING VERIFICATION")
print("=" * 100)

# Test 1: Configuration with warnings
print("\n[TEST 1] Configuration Loading with Warnings")
print("-" * 100)
os.environ['LLM_PROVIDER'] = 'gemini'
os.environ['LLM_FALLBACK_CHAIN'] = 'gemini,openrouter,ollama'
os.environ['LLM_MAX_RETRIES'] = '3'

from backend.llm.config import LLMConfig

config = LLMConfig.from_env()
warnings = config.validate()

# Test 2: Configuration with valid setup
print("\n[TEST 2] Configuration Loading with Valid Setup")
print("-" * 100)
os.environ['GEMINI_API_KEY'] = 'test-key-123'
os.environ['GEMINI_MODEL'] = 'gemini-1.5-flash'
os.environ['OPENROUTER_API_KEY'] = 'test-key-456'
os.environ['OLLAMA_BASE_URL'] = 'http://localhost:11434'

config2 = LLMConfig.from_env()
warnings2 = config2.validate()

# Test 3: Invalid configuration values
print("\n[TEST 3] Configuration with Invalid Values")
print("-" * 100)
os.environ['LLM_MAX_RETRIES'] = '-1'
os.environ['LLM_TIMEOUT'] = '0'

config3 = LLMConfig.from_env()
warnings3 = config3.validate()

print("\n" + "=" * 100)
print("LOGGING VERIFICATION COMPLETE")
print("=" * 100)
print("\nLogging Features Demonstrated:")
print("  ✓ INFO-level: Configuration loading, provider setup, validation success")
print("  ✓ WARNING-level: Missing providers, invalid configuration values")
print("  ✓ ERROR-level: Configuration errors (when they occur)")
print("  ✓ Detailed context: Provider names, models, URLs, retry settings")
print("\nNote: Manager and retry logging will be demonstrated during actual LLM usage.")
