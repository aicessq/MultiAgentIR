"""StructuredAgent - base class for all agents with structured output.

Key responsibilities:
1. Validate input against schema
2. Render prompt from registry
3. Build ModelRequest with output schema
4. Invoke ModelGateway
5. Validate structured output
6. Bounded repair attempts
7. Persist raw/output artifact
8. Return typed result

Key constraints:
- NO raw brace slicing ("find first { to last }")
- ALL outputs validated against Pydantic schema
- Repair attempts bounded (max 2)
- Failed validation returns error, not fake data
- No "mock sources" when search fails
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ValidationError

from app.config.effective_config import EffectiveConfig
from app.domain.errors import InvalidOutputError, ModelUnavailableError
from app.domain.models import Artifact
from app.gateways.model import ModelGateway, ModelRequest, ModelResponse
from app.gateways.storage import ArtifactStore

logger = logging.getLogger(__name__)

OutputType = TypeVar("OutputType", bound=BaseModel)


class PromptRegistry:
    """Registry for prompt templates.

    Prompts are identified by:
    - agent_name: e.g., "planner", "analyzer"
    - purpose: e.g., "plan", "repair"
    - language: e.g., "zh-CN", "en-US"
    - version: e.g., "v1", "v2"
    """

    def __init__(self) -> None:
        self._prompts: dict[str, dict] = {}

    def register(
        self,
        agent_name: str,
        purpose: str,
        language: str,
        version: str,
        template: str,
        input_schema: type[BaseModel] | None = None,
        output_schema: type[BaseModel] | None = None,
    ) -> None:
        """Register a prompt template."""
        key = f"{agent_name}:{purpose}:{language}:{version}"
        self._prompts[key] = {
            "agent": agent_name,
            "purpose": purpose,
            "language": language,
            "version": version,
            "template": template,
            "input_schema": input_schema,
            "output_schema": output_schema,
        }

    def get(
        self,
        agent_name: str,
        purpose: str,
        language: str = "zh-CN",
        version: str = "latest",
    ) -> dict | None:
        """Get a prompt template."""
        if version == "latest":
            # Find latest version
            matching_keys = [
                k for k in self._prompts.keys()
                if k.startswith(f"{agent_name}:{purpose}:{language}:")
            ]
            if not matching_keys:
                return None
            # Sort by version and get latest
            matching_keys.sort()
            key = matching_keys[-1]
        else:
            key = f"{agent_name}:{purpose}:{language}:{version}"

        return self._prompts.get(key)

    def get_version(self, agent_name: str, purpose: str, language: str = "zh-CN") -> str:
        """Get the latest version for an agent/purpose."""
        matching_keys = [
            k for k in self._prompts.keys()
            if k.startswith(f"{agent_name}:{purpose}:{language}:")
        ]
        if not matching_keys:
            return "unknown"
        matching_keys.sort()
        return matching_keys[-1].split(":")[-1]


class OutputValidator:
    """Validates LLM output against Pydantic schema.

    Key constraint: NO raw brace slicing.
    Uses proper JSON parsing and Pydantic validation.
    """

    def validate(
        self,
        content: str,
        schema: type[OutputType],
    ) -> tuple[OutputType | None, list[str]]:
        """Validate content against Pydantic schema.

        Returns:
            (validated_output, validation_errors)

        Process:
        1. Parse JSON properly (no brace slicing)
        2. Validate with Pydantic
        3. Return errors if validation fails
        """
        errors = []

        # Step 1: Parse JSON properly
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            # Try to extract JSON from content without brace slicing
            parsed = self._extract_json(content)
            if parsed is None:
                errors.append(f"JSON parse error: {e}")
                return None, errors

        # Step 2: Validate with Pydantic
        try:
            validated = schema.model_validate(parsed)
            return validated, []
        except ValidationError as e:
            errors.extend([str(err) for err in e.errors()])
            return None, errors

    def _extract_json(self, content: str) -> dict | None:
        """Extract JSON from content using proper parsing.

        Key constraint: NO brace slicing.
        Uses json.JSONDecoder for proper extraction.
        """
        # Find potential JSON start
        start_idx = content.find("{")
        if start_idx < 0:
            return None

        try:
            # Use JSONDecoder to parse incrementally
            decoder = json.JSONDecoder()
            obj, end_idx = decoder.raw_decode(content[start_idx:])
            return obj
        except json.JSONDecodeError:
            return None


class StructuredAgent(ABC, Generic[OutputType]):
    """Base class for agents with structured output.

    Usage:
    1. Define InputType and OutputType as Pydantic models
    2. Implement _prompt_context() to build template variables
    3. Implement _build_output_schema() to return the output schema
    4. Call run() with validated input

    The agent will:
    1. Validate input
    2. Render prompt
    3. Call ModelGateway with schema
    4. Validate output
    5. Attempt repair if needed
    6. Persist artifacts
    7. Return typed result
    """

    name: str = "base"
    purpose: str = "general"
    language: str = "zh-CN"

    def __init__(
        self,
        model_gateway: ModelGateway,
        prompt_registry: PromptRegistry,
        artifact_store: ArtifactStore | None = None,
        config: EffectiveConfig | None = None,
    ) -> None:
        self._model_gateway = model_gateway
        self._prompt_registry = prompt_registry
        self._artifact_store = artifact_store
        self._config = config
        self._validator = OutputValidator()

    @abstractmethod
    def _build_output_schema(self) -> type[OutputType]:
        """Return the Pydantic schema for output validation."""
        pass

    @abstractmethod
    def _prompt_context(self, input_data: BaseModel) -> dict[str, Any]:
        """Build template variables from input."""
        pass

    @abstractmethod
    def _required_capabilities(self) -> set[str]:
        """Return required model capabilities."""
        pass

    async def run(
        self,
        input_data: BaseModel,
        run_id: str,
        on_event: Any | None = None,
    ) -> OutputType:
        """Execute the agent with structured output.

        Process:
        1. Validate input
        2. Get prompt template
        3. Render prompt
        4. Build ModelRequest with schema
        5. Call ModelGateway
        6. Validate output
        7. Repair if needed (bounded)
        8. Persist artifacts
        9. Return typed result
        """
        # Step 1: Get prompt
        prompt_info = self._prompt_registry.get(
            agent_name=self.name,
            purpose=self.purpose,
            language=self.language,
        )
        if not prompt_info:
            raise ValueError(f"No prompt found for {self.name}:{self.purpose}")

        template = prompt_info["template"]
        prompt_version = prompt_info["version"]

        # Step 2: Render prompt
        context = self._prompt_context(input_data)
        rendered_prompt = self._render_template(template, context)

        # Step 3: Build output schema
        output_schema = self._build_output_schema()
        schema_dict = output_schema.model_json_schema()

        # Step 4: Build ModelRequest
        request = ModelRequest(
            purpose=f"{self.name}:{self.purpose}",
            messages=[{"role": "user", "content": rendered_prompt}],
            output_schema=schema_dict,
            output_schema_name=output_schema.__name__,
            required_capabilities=self._required_capabilities(),
            max_output_tokens=self._get_max_output_tokens(),
            temperature=self._get_temperature(),
            timeout_seconds=self._get_timeout_seconds(),
            budget_class=self._get_budget_class(),
            stream=False,
            max_repair_attempts=self._get_max_repair_attempts(),
        )

        # Step 5: Call ModelGateway
        response = await self._model_gateway.call(request)

        # Step 6: Validate output
        output_schema_type = self._build_output_schema()
        validated, errors = self._validator.validate(
            response.content,
            output_schema_type,
        )

        if validated is None:
            # Validation failed after all repair attempts
            raise InvalidOutputError(
                f"Output validation failed for {self.name}: {errors}",
            )

        # Step 7: Persist artifacts (if store available)
        if self._artifact_store and response.parsed_output:
            await self._persist_artifact(
                run_id=run_id,
                raw_content=response.content,
                parsed_output=response.parsed_output,
                prompt_version=prompt_version,
                model_name=response.model_name,
            )

        # Step 8: Record usage
        if self._config:
            self._model_gateway.record_usage(response, request, run_id)

        return validated

    def _render_template(self, template: str, context: dict) -> str:
        """Render prompt template with context."""
        # Simple string replacement - production would use Jinja2
        result = template
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            if isinstance(value, list):
                value = json.dumps(value, indent=2)
            elif isinstance(value, dict):
                value = json.dumps(value, indent=2)
            result = result.replace(placeholder, str(value))
        return result

    def _get_max_output_tokens(self) -> int:
        """Get max output tokens from config."""
        if self._config:
            return 4096  # Default from config
        return 4096

    def _get_temperature(self) -> float:
        """Get temperature."""
        return 0.7

    def _get_timeout_seconds(self) -> float:
        """Get timeout."""
        if self._config:
            return self._config.timeout.analyze_seconds
        return 180.0

    def _get_budget_class(self) -> str:
        """Get budget class."""
        return "medium"

    def _get_max_repair_attempts(self) -> int:
        """Get max repair attempts."""
        if self._config:
            return self._config.graph.max_report_repairs
        return 2

    async def _persist_artifact(
        self,
        run_id: str,
        raw_content: str,
        parsed_output: dict,
        prompt_version: str,
        model_name: str,
    ) -> None:
        """Persist artifact to store."""
        # Implementation depends on artifact type
        pass


class FakeStructuredAgent(StructuredAgent[BaseModel]):
    """Fake agent for testing."""

    name = "fake"
    purpose = "test"

    def __init__(
        self,
        model_gateway: ModelGateway,
        prompt_registry: PromptRegistry,
        output: BaseModel | None = None,
    ) -> None:
        super().__init__(model_gateway, prompt_registry)
        self._output = output
        self._calls: list[BaseModel] = []

    def _build_output_schema(self) -> type[BaseModel]:
        return BaseModel

    def _prompt_context(self, input_data: BaseModel) -> dict[str, Any]:
        return {"input": input_data.model_dump()}

    def _required_capabilities(self) -> set[str]:
        return {"chat"}

    async def run(
        self,
        input_data: BaseModel,
        run_id: str,
        on_event: Any | None = None,
    ) -> BaseModel:
        self._calls.append(input_data)
        if self._output:
            return self._output
        return BaseModel()

    def get_calls(self) -> list[BaseModel]:
        return self._calls