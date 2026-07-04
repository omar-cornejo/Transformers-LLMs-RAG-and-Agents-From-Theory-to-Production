from pathlib import Path


class RagAgent:
    def __init__(self):
        self.path_dir = Path(__file__).parent / "data_assist/exercice1/"

    def _read_file(self, name_file: str) -> str:
        path_file = self.path_dir / name_file
        return path_file.read_text(encoding="utf-8").strip()

    def _load_files(self) -> dict:
        return {
            "role": self._read_file("role.md"),
            "rules": self._read_file("rules.md"),
            "output_format": self._read_file("output_format.md"),
            "context": self._read_file("context.md"),
        }

    def get_promt(self, user_input: str) -> str:
        data = self._load_files()
        return (
            f"---\n"
            f"{data['role']}\n"
            f"{data['rules']}\n"
            f"{data['output_format']}\n"
            "# Context\n"
            f"{data['context']} \n"
            f"# User input\n"
            f"{user_input}"
        )
