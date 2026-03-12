# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
import json
from pathlib import Path
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
import yaml
from jinja2 import Template

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from application.ports.prompt_service import PromptService


class Prompt(PromptService):

    def __init__(self) -> None:
        self.prompt_path: Optional[Path] = None
        self.prompt_name: Optional[str] = None
        self.prompt: Optional[Dict[str, Any]] = None

    def load_prompt(self, path: str, name: Optional[str] = None) -> Dict[str, Any]:
        if not path:
            raise FileNotFoundError("Prompt path cannot be empty")

        self.prompt_path = Path(path)
        self.prompt_name = name

        if not self.prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {self.prompt_path}")

        ext = self.prompt_path.suffix.lower()

        try:
            with self.prompt_path.open("r", encoding="utf-8") as f:
                if ext in (".yaml", ".yml"):
                    data = yaml.safe_load(f)
                elif ext == ".json":
                    data = json.load(f)
                else:
                    raise ValueError(f"Unsupported file format: {ext}")

            if not isinstance(data, dict):
                raise ValueError(f"Prompt file {self.prompt_path} must contain a dictionary")

            # Determine which prompt to load
            if len(data) == 1:
                selected_prompt = next(iter(data.values()))

            elif len(data) > 1:
                if not self.prompt_name:
                    raise ValueError(
                        f"Multiple prompts found in {self.prompt_path}. "
                        "Please provide 'name'."
                    )

                if self.prompt_name not in data:
                    raise ValueError(
                        f"Prompt name '{self.prompt_name}' not found in {self.prompt_path}"
                    )

                selected_prompt = data[self.prompt_name]

            else:
                raise ValueError(f"No prompts found in {self.prompt_path}")

            if not isinstance(selected_prompt, dict):
                raise ValueError("Selected prompt must be a dictionary")

            self.prompt = selected_prompt
            return self.prompt

        except Exception as e:
            raise ValueError(f"Error loading prompt file {self.prompt_path}: {e}") from e

    def get_prompt(self, **kwargs) -> Dict[str, Any]:
        if not self.prompt:
            raise RuntimeError("Prompt not loaded. Call load_prompt() first.")

        sys_template = Template(self.prompt.get("system", ""))
        usr_template = Template(self.prompt.get("user", ""))

        rendered = {
            "system": sys_template.render(**kwargs),
            "user": usr_template.render(**kwargs),
        }

        if "schema" in self.prompt:
            rendered["schema"] = self.prompt["schema"]

        return rendered


if __name__ == "__main__":

    prompt = Prompt()
    prompt.load_prompt("src/prompts/predict_sheet_data.yaml")

    data = {
        "sheet_name": {
            "palabras_clave": ["palabra1", "palabra2", "..."]
        },
        "otra_sheet_name": {
            "palabras_clave": ["palabra1", "palabra2", "..."]
        }
    }

    rendered = prompt.get_prompt(input_data=data)
    print(rendered)