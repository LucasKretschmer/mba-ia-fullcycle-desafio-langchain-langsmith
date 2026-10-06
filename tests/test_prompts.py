"""
Testes automatizados para validação de prompts.
"""
import re
import pytest
import yaml
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import validate_prompt_structure

PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "bug_to_user_story_v2.yml"
PROMPT_KEY = "bug_to_user_story_v2"


def load_prompts(file_path: str):
    """Carrega prompts do arquivo YAML."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def prompt():
    data = load_prompts(PROMPT_FILE)
    assert PROMPT_KEY in data, f"Chave '{PROMPT_KEY}' não encontrada no YAML"
    return data[PROMPT_KEY]


@pytest.fixture(scope="module")
def system_prompt(prompt):
    return prompt.get("system_prompt", "")


class TestPrompts:
    def test_prompt_has_system_prompt(self, prompt):
        """Verifica se o campo 'system_prompt' existe e não está vazio."""
        assert "system_prompt" in prompt
        assert isinstance(prompt["system_prompt"], str)
        assert prompt["system_prompt"].strip()

    def test_prompt_has_role_definition(self, system_prompt):
        """Verifica se o prompt define uma persona (ex: "Você é um Product Manager")."""
        assert re.search(r"Você é (um|uma) ", system_prompt), "Persona não definida"
        assert "Product Manager" in system_prompt

    def test_prompt_mentions_format(self, system_prompt):
        """Verifica se o prompt exige formato Markdown ou User Story padrão."""
        text = system_prompt.lower()
        assert "markdown" in text or "user story" in text
        for part in ["como um", "eu quero", "para que"]:
            assert part in text, f"Formato de User Story sem '{part}'"
        assert "critérios de aceitação" in text

    def test_prompt_has_few_shot_examples(self, system_prompt):
        """Verifica se o prompt contém exemplos de entrada/saída (técnica Few-shot)."""
        assert "exemplo" in system_prompt.lower()
        inputs = system_prompt.count("Relato:")
        outputs = system_prompt.count("Resposta:")
        assert inputs >= 2, "Few-shot precisa de pelo menos 2 exemplos"
        assert inputs == outputs, "Cada exemplo precisa ter entrada e saída"

    def test_prompt_no_todos(self, prompt):
        """Garante que você não esqueceu nenhum `[TODO]` no texto."""
        for field in ["description", "system_prompt", "user_prompt"]:
            assert "[TODO]" not in prompt.get(field, ""), f"[TODO] encontrado em {field}"
            assert "TODO" not in prompt.get(field, "")

    def test_minimum_techniques(self, prompt):
        """Verifica (através dos metadados do yaml) se pelo menos 2 técnicas foram listadas."""
        techniques = prompt.get("techniques_applied", [])
        assert isinstance(techniques, list)
        assert len(techniques) >= 2
        assert "Few-shot Learning" in techniques

    def test_user_prompt_has_bug_report_variable(self, prompt):
        assert "{bug_report}" in prompt.get("user_prompt", "")
        assert "{bug_report}" not in prompt.get("system_prompt", "")

    def test_prompt_structure_is_valid(self, prompt):
        is_valid, errors = validate_prompt_structure(prompt)
        assert is_valid, errors


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
