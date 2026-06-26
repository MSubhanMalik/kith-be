from openai import AsyncOpenAI, RateLimitError, APITimeoutError, APIConnectionError

from app.config import settings


class LLMClient:
    def __init__(self):
        self.primary = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY or "not-set",
            base_url="https://openrouter.ai/api/v1",
            timeout=None,
        )

        self.fallback = None
        if settings.GROQ_API_KEY:
            self.fallback = AsyncOpenAI(
                api_key=settings.GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1",
                timeout=None,
            )

    async def chat(self, messages, model=None, tools=None, response_format=None, temperature=0.7, max_tokens=2048):
        model = model or settings.OPENROUTER_MODEL_SMART
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if response_format:
            kwargs["response_format"] = response_format

        return await self.primary.chat.completions.create(**kwargs)

    async def chat_with_fallback(self, messages, model=None, tools=None, response_format=None, temperature=0.7, max_tokens=2048):
        try:
            return await self.chat(messages, model, tools, response_format, temperature, max_tokens)
        except (RateLimitError, APITimeoutError, APIConnectionError):
            if self.fallback:
                fallback_model = settings.GROQ_MODEL
                kwargs = {
                    "model": fallback_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if tools:
                    kwargs["tools"] = tools
                if response_format:
                    kwargs["response_format"] = response_format
                return await self.fallback.chat.completions.create(**kwargs)
            raise
