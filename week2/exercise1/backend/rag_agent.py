from pathlib import Path
import re


class RagAgent:
    def __init__(self):
        self.path_dir = Path(__file__).parent / "data_assist/exercice1/"
        self.scope_keywords = {
            "beast",
            "gohan beast",
            "gohan",
            "ultimate",
            "ultimate gohan",
            "cell max",
            "orange piccolo",
            "dragon ball super: super hero",
            "super hero",
            "manga",
            "transformation",
            "awakening",
            "special beam cannon",
            "makankosappo",
            "trivia",
            "aura",
            "voice",
            "power",
            "xenoverse 2",
        }

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

    def is_in_scope(self, user_input: str) -> bool:
        normalized_input = user_input.lower()
        if not normalized_input.strip():
            return False

        for keyword in self.scope_keywords:
            if keyword in normalized_input:
                return True

        input_words = set(re.findall(r"[a-z0-9]+", normalized_input))
        return any(word in input_words for word in {"beast", "gohan", "ultimate", "cell", "xenoverse"})

    def get_supported_topics(self) -> list:
        """Return a sorted, human-friendly list of supported topics derived from the scope keywords."""
        topics = sorted(self.scope_keywords)
        # Simple normalization for display
        return [t.title() for t in topics]
