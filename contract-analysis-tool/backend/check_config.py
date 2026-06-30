from app.config import get_settings
settings = get_settings()
print(f'LiteLLM Proxy URL: {settings.litellm_proxy_url}')
print(f'LiteLLM API Key length: {len(settings.litellm_api_key)}')
print(f'Use LiteLLM: {settings.use_litellm}')
print(f'LLM Model: {settings.llm_model}')
