# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
import json
from pathlib import Path
from typing import Any, Dict, Union

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

    def __init__(
        self,
        file_path: Union[str, Path],
        **kwargs
    ) -> None:
        self.prompt_path: Path = Path(file_path)
        self.prompt_name: str = kwargs.get("prompt_name", None)
        self.prompt: Dict[str, Any] = self.load_prompt()


    def load_prompt(self) -> Dict[str, Any]:
        if not self.prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {self.prompt_path}")

        ext = self.prompt_path.suffix.lower()
        try:
            with self.prompt_path.open("r", encoding="utf-8") as f:
                if ext in [".yaml", ".yml"]:
                    data = yaml.safe_load(f)
                elif ext == ".json":
                    data = json.load(f)
                else:
                    raise ValueError(f"Unsupported file format: {ext}")

            if not isinstance(data, dict):
                raise ValueError(f"Prompt file {self.prompt_path} must contain a dictionary")

            # Automatically select the first prompt if only one exists
            if len(data) == 1:
                return next(iter(data.values()))
            elif len(data) > 1:
                if not self.prompt_name:
                    raise ValueError(
                        f"Multiple prompts found in {self.prompt_path}, please provide 'prompt_name'"
                    )
                if self.prompt_name not in data:
                    raise ValueError(f"Prompt name '{self.prompt_name}' not found in {self.prompt_path}")
                return data[self.prompt_name]

            return data
        except Exception as e:
            raise ValueError(f"Error loading prompt file {self.prompt_path}: {e}")


    def get_prompt(self, **kwargs) -> Dict[str, Any]:
        if not isinstance(self.prompt, dict):
            raise ValueError("Loaded prompt must be a dictionary with 'system' and 'user' keys")

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

    prompt = Prompt(
        file_path="src/prompts/predict_sheet_data.yaml",
    )
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