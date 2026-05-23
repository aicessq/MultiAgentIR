from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import BASE_DIR

PROMPTS_DIR = BASE_DIR / "prompts"


class PromptLoader:
    def __init__(self) -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(PROMPTS_DIR)),
            autoescape=select_autoescape([]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, template_name: str, **kwargs: object) -> str:
        tpl = self._env.get_template(template_name)
        return tpl.render(**kwargs)

    def get_version(self, template_name: str) -> str:
        path = PROMPTS_DIR / template_name
        if path.exists():
            import hashlib
            return hashlib.md5(path.read_bytes()).hexdigest()[:8]
        return "unknown"
