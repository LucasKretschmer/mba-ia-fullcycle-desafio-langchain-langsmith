"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descrição, técnicas utilizadas)
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client
from langchain_core.prompts import ChatPromptTemplate
from utils import load_yaml, check_env_vars, print_section_header

load_dotenv()

PROMPT_KEY = "bug_to_user_story_v2"
PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / f"{PROMPT_KEY}.yml"
REQUIRED_FIELDS = ["description", "system_prompt", "user_prompt", "version", "techniques_applied"]


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt
        prompt_data: Dados do prompt

    Returns:
        True se sucesso, False caso contrário
    """
    username = os.getenv("USERNAME_LANGSMITH_HUB")
    full_name = f"{username}/{prompt_name}"

    prompt = ChatPromptTemplate.from_messages([
        ("system", prompt_data["system_prompt"]),
        ("user", prompt_data["user_prompt"]),
    ])

    techniques = prompt_data.get("techniques_applied", [])
    tags = list(dict.fromkeys(
        prompt_data.get("tags", [])
        + [prompt_data["version"]]
        + [t.lower().replace(" ", "-") for t in techniques]
    ))

    description = prompt_data["description"].strip()
    if techniques:
        description += f"\n\nTécnicas: {', '.join(techniques)}"

    try:
        client = Client()
        url = client.push_prompt(
            full_name,
            object=prompt,
            is_public=True,
            description=description,
            readme=prompt_data.get("readme"),
            tags=tags,
        )
    except Exception as e:
        message = str(e)
        if "Nothing to commit" in message or "409" in message:
            print(f"ℹ️  Nenhuma alteração desde o último push de {full_name}")
            return True
        print(f"❌ Erro ao fazer push de {full_name}: {e}")
        return False

    print(f"✓ Push realizado: {full_name}")
    print(f"  Tags: {', '.join(tags)}")
    print(f"  {url}")
    return True


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura básica de um prompt (versão simplificada).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    errors = []

    for field in REQUIRED_FIELDS:
        value = prompt_data.get(field)
        if not value or (isinstance(value, str) and not value.strip()):
            errors.append(f"Campo obrigatório vazio ou ausente: {field}")

    system_prompt = prompt_data.get("system_prompt", "")
    user_prompt = prompt_data.get("user_prompt", "")

    if "{bug_report}" not in user_prompt:
        errors.append("user_prompt precisa conter a variável {bug_report}")

    if "{bug_report}" in system_prompt:
        errors.append("{bug_report} deve ficar só no user_prompt")

    if "TODO" in system_prompt or "TODO" in user_prompt:
        errors.append("Prompt ainda contém TODOs")

    if len(prompt_data.get("techniques_applied", [])) < 2:
        errors.append("Liste pelo menos 2 técnicas em techniques_applied")

    return (len(errors) == 0, errors)


def main():
    """Função principal"""
    print_section_header("PUSH DE PROMPTS PARA O LANGSMITH")

    if not check_env_vars(["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]):
        return 1

    data = load_yaml(str(PROMPT_PATH))
    if not data or PROMPT_KEY not in data:
        print(f"❌ Chave '{PROMPT_KEY}' não encontrada em {PROMPT_PATH}")
        return 1

    prompt_data = data[PROMPT_KEY]

    is_valid, errors = validate_prompt(prompt_data)
    if not is_valid:
        print("❌ Prompt inválido:")
        for error in errors:
            print(f"   - {error}")
        return 1

    print(f"✓ {PROMPT_KEY} validado")
    return 0 if push_prompt_to_langsmith(PROMPT_KEY, prompt_data) else 1


if __name__ == "__main__":
    sys.exit(main())
