from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncGenerator

import httpx
from pydantic import BaseModel

from app.schemas.model import ModelSpec

logger = logging.getLogger(__name__)

PROVIDER_ENDPOINTS: dict[str, str] = {
    "anthropic": "/messages",
    "default": "/chat/completions",
}


class LLMCallResult(BaseModel):
    content: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    model_name: str = ""


class StreamResult:
    """Collects usage stats from a streaming LLM call."""
    def __init__(self) -> None:
        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0
        self.latency_ms: float = 0.0


class LLMClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=120.0)

    async def invoke(
        self,
        model: ModelSpec,
        prompt: str,
        system_prompt: str = "",
        api_key: str = "",
    ) -> LLMCallResult:
        if model.provider == "anthropic":
            return await self._call_anthropic(model, prompt, system_prompt, api_key)
        return await self._call_openai_compatible(model, prompt, system_prompt, api_key)

    async def stream(
        self,
        model: ModelSpec,
        prompt: str,
        system_prompt: str = "",
        api_key: str = "",
        result_collector: StreamResult | None = None,
    ) -> AsyncGenerator[str, None]:
        if model.provider == "anthropic":
            async for chunk in self._stream_anthropic(model, prompt, system_prompt, api_key, result_collector):
                yield chunk
        else:
            async for chunk in self._stream_openai(model, prompt, system_prompt, api_key, result_collector):
                yield chunk

    async def _stream_openai(
        self, model: ModelSpec, prompt: str, system_prompt: str, api_key: str,
        result_collector: StreamResult | None,
    ) -> AsyncGenerator[str, None]:
        import os
        base_url = model.api_base or ""
        if not base_url:
            # Try slot-based env var fallback
            for slot in ["search", "analysis", "reasoning", "writing"]:
                val = os.getenv(f"MODEL_{slot.upper()}_API_BASE", "")
                if val:
                    base_url = val
                    break
        if not base_url:
            base_url = "https://api.openai.com/v1"
        base_url = base_url.rstrip("/")
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        body = {"model": model.name, "messages": messages, "temperature": 0.3, "stream": True, "max_tokens": model.max_tokens}

        start = time.perf_counter()
        try:
            async with self._client.stream("POST", f"{base_url}/chat/completions", json=body, headers=headers) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        token = delta.get("content", "")
                        if token:
                            yield token
                        # Collect usage from the last chunk if present
                        usage = data.get("usage")
                        if usage and result_collector:
                            result_collector.prompt_tokens = usage.get("prompt_tokens", 0)
                            result_collector.completion_tokens = usage.get("completion_tokens", 0)
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error(f"OpenAI stream failed: {model.name} {elapsed:.0f}ms {e}")
            raise
        finally:
            if result_collector:
                result_collector.latency_ms = round((time.perf_counter() - start) * 1000, 2)

    async def _stream_anthropic(
        self, model: ModelSpec, prompt: str, system_prompt: str, api_key: str,
        result_collector: StreamResult | None,
    ) -> AsyncGenerator[str, None]:
        base_url = (model.api_base or "https://api.anthropic.com/v1").rstrip("/")
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body: dict = {
            "model": model.name,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        }
        if system_prompt:
            body["system"] = system_prompt

        start = time.perf_counter()
        try:
            async with self._client.stream("POST", f"{base_url}/messages", json=body, headers=headers) as resp:
                resp.raise_for_status()
                event_type = ""
                async for line in resp.aiter_lines():
                    if line.startswith("event: "):
                        event_type = line[7:].strip()
                        continue
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    try:
                        data = json.loads(data_str)
                        if event_type == "content_block_delta":
                            token = data.get("delta", {}).get("text", "")
                            if token:
                                yield token
                        elif event_type == "message_delta":
                            usage = data.get("usage", {})
                            if result_collector and usage:
                                result_collector.completion_tokens = usage.get("output_tokens", 0)
                        elif event_type == "message_start":
                            usage = data.get("message", {}).get("usage", {})
                            if result_collector and usage:
                                result_collector.prompt_tokens = usage.get("input_tokens", 0)
                    except (json.JSONDecodeError, KeyError):
                        continue
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error(f"Anthropic stream failed: {model.name} {elapsed:.0f}ms {e}")
            raise
        finally:
            if result_collector:
                result_collector.latency_ms = round((time.perf_counter() - start) * 1000, 2)

    async def _call_openai_compatible(
        self, model: ModelSpec, prompt: str, system_prompt: str, api_key: str,
    ) -> LLMCallResult:
        import os
        base_url = model.api_base or ""
        if not base_url:
            for slot in ["search", "analysis", "reasoning", "writing"]:
                val = os.getenv(f"MODEL_{slot.upper()}_API_BASE", "")
                if val:
                    base_url = val
                    break
        if not base_url:
            base_url = "https://api.openai.com/v1"
        base_url = base_url.rstrip("/")
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        body = {"model": model.name, "messages": messages, "temperature": 0.3, "max_tokens": model.max_tokens}

        start = time.perf_counter()
        try:
            resp = await self._client.post(f"{base_url}/chat/completions", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            elapsed = (time.perf_counter() - start) * 1000
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = data.get("usage", {})
            return LLMCallResult(
                content=content,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                latency_ms=round(elapsed, 2),
                model_name=model.name,
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error(f"LLM call failed: {model.name} {elapsed:.0f}ms {e}")
            raise

    async def _call_anthropic(
        self, model: ModelSpec, prompt: str, system_prompt: str, api_key: str,
    ) -> LLMCallResult:
        base_url = (model.api_base or "https://api.anthropic.com/v1").rstrip("/")
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body: dict = {
            "model": model.name,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            body["system"] = system_prompt

        start = time.perf_counter()
        try:
            resp = await self._client.post(f"{base_url}/messages", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            elapsed = (time.perf_counter() - start) * 1000
            content = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    content += block.get("text", "")
            usage = data.get("usage", {})
            return LLMCallResult(
                content=content,
                prompt_tokens=usage.get("input_tokens", 0),
                completion_tokens=usage.get("output_tokens", 0),
                latency_ms=round(elapsed, 2),
                model_name=model.name,
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error(f"Anthropic call failed: {model.name} {elapsed:.0f}ms {e}")
            raise

    async def close(self) -> None:
        await self._client.aclose()
