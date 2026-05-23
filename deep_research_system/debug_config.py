"""Debug script to check configuration loading."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import get_config, reset_config

# Reset config to force reload
reset_config()

config = get_config()

print("=" * 60)
print("Configuration Debug")
print("=" * 60)

print("\n1. Settings from pydantic:")
print(f"   model_search_name: {config.settings.model_search_name}")
print(f"   model_search_api_key: {config.settings.model_search_api_key[:20]}..." if config.settings.model_search_api_key else "   model_search_api_key: (empty)")
print(f"   model_search_api_base: {config.settings.model_search_api_base}")

print("\n2. Environment variables (os.getenv):")
print(f"   MODEL_SEARCH_API_KEY: {os.getenv('MODEL_SEARCH_API_KEY', '(not set)')[:30]}..." if os.getenv('MODEL_SEARCH_API_KEY') else "   MODEL_SEARCH_API_KEY: (not set)")
print(f"   model_search_api_key: {os.getenv('model_search_api_key', '(not set)')[:30]}..." if os.getenv('model_search_api_key') else "   model_search_api_key: (not set)")

print("\n3. Effective API Keys from config:")
api_keys = config.get_effective_api_keys()
for model, keys in api_keys.items():
    print(f"   {model}:")
    for k in keys:
        print(f"     - key_id: {k.get('key_id')}, env_name: {k.get('env_name')}")

print("\n4. Effective Models from config:")
models = config.get_effective_models()
for m in models:
    print(f"   - name: {m.get('name')}, provider: {m.get('provider')}, api_base: {m.get('api_base')}")

print("\n5. Test APIKeyPool:")
from app.model_pool.key_pool import APIKeyPool
key_pool = APIKeyPool()
for model in ['deepseek-chat', 'gpt-4o']:
    key = key_pool.get_api_key(model)
    print(f"   {model}: {'Found key!' if key else 'No key found'}")
