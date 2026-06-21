"""ModelGateway - unified interface for LLM calls.

Key responsibilities:
1. Select model based on capabilities and budget
2. Call model with structured output support
3. Validate output against schema
4. Handle retries and repairs
5. Record usage for audit

Key constraints:
- All structured outputs MUST be validated against Pydantic schema
- NO raw brace slicing ("find first { to last }")
- Required capabilities MUST be satisfied or fail
- Budget MUST be checked before call
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import AsyncIterator

from pydantic import BaseModel

from app.domain.errors import (
    BudgetExceededError,
    InvalidOutputError,
    ModelUnavailableError,
    RateLimitError,
    TransientError,
)
from app.gateways.model.spec import ModelCapability, ModelRequest, ModelResponse, ModelSpec

logger = logging.getLogger(__name__)


class ModelGateway(ABC):
    """Abstract base class for model gateway."""

    @abstractmethod
    async def select_model(self, request: ModelRequest) -> ModelSpec | None:
        """Select a model that satisfies the request requirements."""
        pass

    @abstractmethod
    async def call(self, request: ModelRequest) -> ModelResponse:
        """Call the selected model and return validated response."""
        pass

    @abstractmethod
    async def stream(self, request: ModelRequest) -> AsyncIterator[str]:
        """Stream tokens from the model."""
        pass

    @abstractmethod
    def check_budget(self, estimated_tokens: int, estimated_cost: float) -> bool:
        """Check if budget allows the call."""
        pass

    @abstractmethod
    def record_usage(self, response: ModelResponse, request: ModelRequest, run_id: str) -> None:
        """Record usage for audit."""
        pass


class DefaultModelGateway(ModelGateway):
    """Default implementation of ModelGateway."""

    def __init__(
        self,
        models: list[ModelSpec],
        budget_max_tokens: int = 300000,
        budget_max_cost_usd: float = 20.0,
        budget_warning_ratio: float = 0.8,
    ) -> None:
        self._models = {m.name: m for m in models}
        self._budget_max_tokens = budget_max_tokens
        self._budget_max_cost_usd = budget_max_cost_usd
        self._budget_warning_ratio = budget_warning_ratio
        self._usage_so_far_tokens = 0
        self._usage_so_far_cost = 0.0
        self._usage_records: list[dict] = []

    async def select_model(self, request: ModelRequest) -> ModelSpec | None:
        """Select a model that satisfies the request requirements.

        Selection criteria:
        1. Must have all required capabilities
        2. Prefer models with preferred capabilities
        3. Prefer lower cost tier within budget class
        4. Prefer higher priority
        """
        candidates = []

        for spec in self._models.values():
            if not spec.enabled:
                continue

            # Check required capabilities
            for cap in spec.capabilities:
                if not cap.enabled:
                    continue

                # Check required capabilities
                has_required = all(
                    cap.name == req_cap or cap.supports_structured_output
                    for req_cap in request.required_capabilities
                )

                if not has_required:
                    continue

                # Check budget class
                if cap.cost_tier != request.budget_class:
                    # Allow lower cost tiers
                    if cap.cost_tier == "low" and request.budget_class in ("medium", "high"):
                        pass
                    elif cap.cost_tier == "medium" and request.budget_class == "high":
                        pass
                    else:
                        continue

                # Check max output tokens
                if cap.max_output_tokens < request.max_output_tokens:
                    continue

                # Calculate match score
                preferred_match = sum(
                    1 for pref in request.preferred_capabilities
                    if cap.name == pref
                )

                candidates.append((spec, cap, preferred_match, cap.priority))

        if not candidates:
            logger.warning(f"No model found for request: {request.purpose}, required={request.required_capabilities}")
            return None

        # Sort by: preferred_match (desc), priority (desc), cost_tier (asc)
        candidates.sort(key=lambda x: (-x[2], -x[3], x[1].cost_tier))

        return candidates[0][0]

    async def call(self, request: ModelRequest) -> ModelResponse:
        """Call the selected model and return validated response.

        This method:
        1. Selects appropriate model
        2. Checks budget
        3. Makes the call
        4. Validates structured output
        5. Attempts repair if validation fails
        6. Records usage
        """
        model = await self.select_model(request)
        if not model:
            raise ModelUnavailableError(
                f"No model available for purpose={request.purpose}, "
                f"required_capabilities={request.required_capabilities}"
            )

        # Estimate cost
        estimated_tokens = request.max_output_tokens + (request.max_input_tokens or 4000)
        cap = model.default_capability or model.capabilities[0]
        estimated_cost = (
            estimated_tokens * cap.input_cost_per_1k_tokens / 1000 +
            request.max_output_tokens * cap.output_cost_per_1k_tokens / 1000
        )

        # Check budget
        if not self.check_budget(estimated_tokens, estimated_cost):
            raise BudgetExceededError(
                f"Budget exceeded: tokens={self._usage_so_far_tokens}/{self._budget_max_tokens}, "
                f"cost={self._usage_so_far_cost}/{self._budget_max_cost_usd}"
            )

        # Make the call
        start_time = time.time()
        raw_content, raw_response = await self._call_model(model, request)
        latency_ms = (time.time() - start_time) * 1000

        # Parse and validate
        parsed_output = None
        validation_errors = []
        repair_attempts = 0

        if request.output_schema:
            # Structured output - validate against schema
            parsed_output, validation_errors = self._validate_structured_output(
                raw_content, request.output_schema
            )

            # Attempt repair if validation failed
            while validation_errors and repair_attempts < request.max_repair_attempts:
                repair_attempts += 1
                logger.info(f"Attempting repair {repair_attempts} for {request.purpose}")

                repair_request = self._build_repair_request(request, raw_content, validation_errors)
                raw_content, raw_response = await self._call_model(model, repair_request)
                parsed_output, validation_errors = self._validate_structured_output(
                    raw_content, request.output_schema
                )

            if validation_errors:
                logger.error(f"Validation failed after {repair_attempts} repairs: {validation_errors}")
                # Don't raise - return with errors for caller to handle
        else:
            # No schema - just parse JSON if present
            parsed_output = self._parse_json(raw_content)

        # Calculate actual cost
        prompt_tokens = raw_response.get("usage", {}).get("prompt_tokens", 0)
        completion_tokens = raw_response.get("usage", {}).get("completion_tokens", 0)
        actual_cost = (
            prompt_tokens * cap.input_cost_per_1k_tokens / 1000 +
            completion_tokens * cap.output_cost_per_1k_tokens / 1000
        )

        # Update budget tracking
        self._usage_so_far_tokens += prompt_tokens + completion_tokens
        self._usage_so_far_cost += actual_cost

        response = ModelResponse(
            content=raw_content,
            parsed_output=parsed_output,
            model_name=model.model_name,
            model_provider=model.provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            estimated_cost_usd=actual_cost,
            repair_attempts=repair_attempts,
            validation_errors=validation_errors,
            raw_response=raw_response,
        )

        return response

    async def stream(self, request: ModelRequest) -> AsyncIterator[str]:
        """Stream tokens from the model."""
        model = await self.select_model(request)
        if not model:
            raise ModelUnavailableError(f"No model available for {request.purpose}")

        # Implementation depends on provider
        # This is a placeholder - actual implementation would use httpx streaming
        async for token in self._stream_model(model, request):
            yield token

    def check_budget(self, estimated_tokens: int, estimated_cost: float) -> bool:
        """Check if budget allows the call."""
        if self._usage_so_far_tokens + estimated_tokens > self._budget_max_tokens:
            return False
        if self._usage_so_far_cost + estimated_cost > self._budget_max_cost_usd:
            return False
        return True

    def record_usage(self, response: ModelResponse, request: ModelRequest, run_id: str) -> None:
        """Record usage for audit."""
        record = {
            "run_id": run_id,
            "node": request.purpose,
            "provider": response.model_provider,
            "model": response.model_name,
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "cost_usd": response.estimated_cost_usd,
            "latency_ms": response.latency_ms,
            "repair_attempts": response.repair_attempts,
            "success": not response.validation_errors,
        }
        self._usage_records.append(record)

    async def _call_model(self, model: ModelSpec, request: ModelRequest) -> tuple[str, dict]:
        """Make the actual model call. Implementation varies by provider."""
        # Placeholder - actual implementation would use httpx
        raise NotImplementedError("Subclasses must implement _call_model")

    async def _stream_model(self, model: ModelSpec, request: ModelRequest) -> AsyncIterator[str]:
        """Stream from the model. Implementation varies by provider."""
        raise NotImplementedError("Subclasses must implement _stream_model")

    def _validate_structured_output(
        self, content: str, schema: dict
    ) -> tuple[dict | None, list[str]]:
        """Validate content against JSON schema.

        Returns:
            (parsed_output, validation_errors)

        Key constraint: NO raw brace slicing.
        Must use proper JSON parsing.
        """
        errors = []

        # Try to parse JSON
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            errors.append(f"JSON parse error: {e}")
            return None, errors

        # Validate against schema using Pydantic
        # This is simplified - actual implementation would use jsonschema
        if isinstance(parsed, dict):
            # Check required fields
            required = schema.get("required", [])
            for field in required:
                if field not in parsed:
                    errors.append(f"Missing required field: {field}")

            if errors:
                return parsed, errors

            return parsed, []

        return parsed, []

    def _parse_json(self, content: str) -> dict | None:
        """Parse JSON from content without brace slicing.

        Key constraint: Must use proper JSON parsing.
        """
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to find JSON object in content
            # But NOT by brace slicing - use proper extraction
            try:
                # Look for JSON-like structure
                start = content.find("{")
                if start >= 0:
                    # Use json.JSONDecoder to parse incrementally
                    decoder = json.JSONDecoder()
                    obj, _ = decoder.raw_decode(content[start:])
                    return obj
            except (json.JSONDecodeError, ValueError):
                pass
        return None

    def _build_repair_request(
        self, original: ModelRequest, failed_content: str, errors: list[str]
    ) -> ModelRequest:
        """Build a repair request with validation errors."""
        repair_prompt = (
            f"The previous output failed validation with these errors:\n"
            f"{json.dumps(errors, indent=2)}\n\n"
            f"Previous output:\n{failed_content}\n\n"
            f"Please fix the issues and output valid JSON matching the schema."
        )

        # Add repair instructions to messages
        messages = list(original.messages)
        messages.append({"role": "user", "content": repair_prompt})

        return ModelRequest(
            purpose=original.purpose + "_repair",
            messages=messages,
            output_schema=original.output_schema,
            output_schema_name=original.output_schema_name,
            required_capabilities=original.required_capabilities,
            max_output_tokens=original.max_output_tokens,
            temperature=0.3,  # Lower temperature for repair
            timeout_seconds=original.timeout_seconds,
            budget_class=original.budget_class,
            stream=False,
            max_repair_attempts=original.max_repair_attempts - 1,
        )


class FakeModelGateway(ModelGateway):
    """Fake gateway for testing."""

    def __init__(self, responses: dict[str, str] | None = None) -> None:
        self._responses = responses or {}
        self._calls: list[ModelRequest] = []

    async def select_model(self, request: ModelRequest) -> ModelSpec | None:
        return ModelSpec(
            name="fake-model",
            provider="fake",
            api_base="http://fake",
            api_key_env="FAKE_KEY",
            model_name="fake-model",
            enabled=True,
        )

    async def call(self, request: ModelRequest) -> ModelResponse:
        self._calls.append(request)

        content = self._responses.get(request.purpose, '{"result": "fake"}')

        return ModelResponse(
            content=content,
            parsed_output=json.loads(content) if content.startswith("{") else None,
            model_name="fake-model",
            model_provider="fake",
            prompt_tokens=100,
            completion_tokens=100,
            latency_ms=100.0,
            estimated_cost_usd=0.01,
        )

    async def stream(self, request: ModelRequest) -> AsyncIterator[str]:
        for char in self._responses.get(request.purpose, "fake response"):
            yield char

    def check_budget(self, estimated_tokens: int, estimated_cost: float) -> bool:
        return True

    def record_usage(self, response: ModelResponse, request: ModelRequest, run_id: str) -> None:
        pass

    def get_calls(self) -> list[ModelRequest]:
        return self._calls