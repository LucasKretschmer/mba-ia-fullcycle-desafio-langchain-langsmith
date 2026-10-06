"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull do prompt semente do desafio
3. Salva localmente em prompts/bug_to_user_story_v1.yml
"""

import os
import sys
from datetime import date
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client
from utils import save_yaml, check_env_vars, print_section_header

load_dotenv()

SOURCE_PROMPT = "leonanluppi/bug_to_user_story_v1"
PROMPT_KEY = "bug_to_user_story_v1"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "prompts" / f"{PROMPT_KEY}.yml"


def extract_messages(prompt) -> dict:
    messages = {"system_prompt": "", "user_prompt": ""}

    for message in prompt.messages:
        template = getattr(getattr(message, "prompt", None), "template", None)
        if template is None:
            continue

        kind = type(message).__name__
        if kind.startswith("System"):
            messages["system_prompt"] = template
        elif kind.startswith("Human"):
            messages["user_prompt"] = template

    return messages


def pull_prompts_from_langsmith():
    client = Client()

    print(f"Fazendo pull de: {SOURCE_PROMPT}")
    prompt = client.pull_prompt(SOURCE_PROMPT, dangerously_pull_public_prompt=True)

    messages = extract_messages(prompt)
    if not messages["system_prompt"]:
        raise ValueError("Prompt retornado sem mensagem de system")

    metadata = getattr(prompt, "metadata", None) or {}

    data = {
        PROMPT_KEY: {
            "description": metadata.get("lc_hub_description")
            or "Prompt para converter relatos de bugs em User Stories",
            "system_prompt": messages["system_prompt"],
            "user_prompt": messages["user_prompt"],
            "input_variables": list(prompt.input_variables),
            "version": "v1",
            "source": SOURCE_PROMPT,
            "pulled_at": date.today().isoformat(),
            "tags": ["bug-analysis", "user-story", "product-management"],
        }
    }

    if not save_yaml(data, str(OUTPUT_PATH)):
        raise IOError(f"Não foi possível salvar {OUTPUT_PATH}")

    return data


def main():
    """Função principal"""
    print_section_header("PULL DE PROMPTS DO LANGSMITH")

    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return 1

    try:
        data = pull_prompts_from_langsmith()
    except Exception as e:
        print(f"❌ Erro ao fazer pull do prompt: {e}")
        return 1

    prompt = data[PROMPT_KEY]
    print(f"✓ Variáveis de entrada: {prompt['input_variables']}")
    print(f"✓ Prompt salvo em: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
