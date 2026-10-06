# Pull, Otimização e Avaliação de Prompts com LangChain e LangSmith

Projeto do desafio do MBA em IA (Full Cycle). O fluxo é:

1. Pull do prompt `leonanluppi/bug_to_user_story_v1` do LangSmith Prompt Hub
2. Refatoração do prompt em `prompts/bug_to_user_story_v2.yml`
3. Push da v2 para o Hub (`<meu_handle>/bug_to_user_story_v2`, público)
4. Avaliação com 5 métricas (Helpfulness, Correctness, F1-Score, Clarity e Precision) até todas ficarem >= 0.8

O prompt converte relatos de bugs em User Stories com critérios de aceitação.

---

## Técnicas Aplicadas (Fase 2)

### Problemas da v1

| Problema na v1 | Efeito |
|---|---|
| `{bug_report}` duplicado no system e no user prompt | O modelo recebe o relato duas vezes, o que gasta tokens e mistura instrução com dado |
| Persona genérica ("um assistente") | Respostas com vocabulário de suporte, não de produto |
| Sem formato definido | Cada resposta saía com uma estrutura diferente, e a nota de Clarity caía |
| Sem exemplos | O modelo não sabia o nível de detalhe esperado |
| Sem regras | O modelo inventava detalhes (alucinação), o que derruba a Precision |
| Sem tratamento de casos especiais | Relatos complexos (vários bugs) viravam uma story só, sem critérios para cada problema |

### 1. Role Prompting

**Por quê:** escrever User Stories é tarefa de Product Manager. Uma persona de PM com conhecimento técnico faz o modelo focar no valor para o usuário ("eu quero adicionar produtos ao carrinho") e não no defeito ("eu quero que o botão pare de falhar"). Ao mesmo tempo, ela não ignora os detalhes técnicos do relato.

**Como apliquei:**
```
Você é um Product Manager sênior com experiência em times ágeis e forte conhecimento
técnico (web, mobile, APIs, banco de dados e segurança)...
```

### 2. Few-shot Learning

**Por quê:** é obrigatória no desafio e é a técnica com mais impacto aqui. O dataset tem três níveis de complexidade, e cada nível tem um formato de resposta esperado diferente. Descrever esses formatos só em texto não basta: os exemplos mostram o tamanho certo da resposta e as seções que cada nível usa.

**Como apliquei:** coloquei 3 exemplos de entrada e saída no system prompt, um para cada nível (simples, médio e complexo). Escrevi exemplos **diferentes** dos casos do dataset (recuperação de senha, CPF com pontuação e renovação de assinatura) para não "vazar" a resposta da avaliação no prompt.

### 3. Chain of Thought

**Por quê:** para converter um bug, é preciso identificar a persona afetada, o comportamento esperado, o benefício e os dados concretos do relato. Quando o modelo segue esses passos antes de escrever, ele erra menos a persona e esquece menos dados (o que melhora o F1/recall).

**Como apliquei:** criei uma seção "Processo de análise" com 5 passos. Ela pede que o raciocínio seja feito **internamente**, sem aparecer na resposta. Se o raciocínio aparecesse no texto final, as notas de Clarity e Precision cairiam.

### 4. Skeleton of Thought

**Por quê:** o avaliador compara a resposta com uma referência que tem estrutura fixa: frase "Como um... eu quero... para que...", "Critérios de Aceitação" em Dado/Quando/Então e, nos casos complexos, seções `=== ... ===`. Definir esse esqueleto antes da escrita deixa a saída previsível e parecida com a referência.

**Como apliquei:** a seção "Formato da resposta" define o esqueleto de cada nível de complexidade, incluindo as seções opcionais permitidas no nível médio (Contexto Técnico, Exemplo de Cálculo etc.).

### Outras decisões

- **System x User:** as instruções, as regras e os exemplos ficam no system prompt. O user prompt tem só o `{bug_report}`, delimitado por aspas triplas.
- **Regras explícitas:** usar os dados do relato sem alterar, não inventar fatos, critérios verificáveis, regras específicas para bugs de segurança e de cálculo.
- **Casos especiais:** relato vago, relato com vários bugs, relato que já sugere a solução, relato em inglês e texto que não é um bug.

---

## Resultados Finais

### Evidências no LangSmith

- Dataset de avaliação (público, com os experimentos): https://smith.langchain.com/public/19631f3e-254a-4a7d-b2c1-0578b5102b09/d
- Prompt v2 no Hub: https://smith.langchain.com/hub/lucaskretschmer/bug_to_user_story_v2

### Screenshots

Resultado do `evaluate.py` no terminal (prompt v2 final, todas as métricas >= 0.8):

![Terminal - início da avaliação](<docs/Print Terminal 1.png>)
![Terminal - notas finais](<docs/Print Terminal 2.png>)

Comparação dos experimentos no LangSmith (#1 erro de execução, #2 e #3 aprovados):

![Experimentos no LangSmith](<docs/Graficos de comprovação de melhora de desempenho.png>)

Notas por exemplo do experimento da iteração #3 (15/15 runs):

![Avaliações por exemplo](<docs/Avaliações realizadas.png>)

Tracing detalhado de 3 exemplos (entrada, chamada ao `gemini-2.5-flash`, saída e notas do avaliador):

![Trace 1 - modal atrás do menu lateral](<docs/Trace 1.png>)
![Trace 2 - app offline-first (complexo)](<docs/Trace 2.png>)
![Trace 3 - validação de email](<docs/Trace 3.png>)

### Iterações

| Iteração | O que mudou no prompt | Helpfulness | Correctness | F1 | Clarity | Precision |
|---|---|---|---|---|---|---|
| v2 #1 (gemini-3.8-flash) | Primeira versão da v2 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| v2 #2 (gemini-2.5-flash) | Mesmo prompt, troca de modelo | 0.96 | 0.91 | 0.85 | 0.96 | 0.96 |

Na iteração #1, todas as notas deram 0 por erro de execução, não por qualidade do prompt. Com modelos Gemini 3+, o `langchain-google-genai` devolve `response.content` como uma lista de blocos (texto + assinatura do raciocínio), e o `metrics.py` espera uma string (`the JSON object must be str ... not list`). Como `metrics.py` e `evaluate.py` não podem ser alterados, testei os modelos disponíveis e troquei `LLM_MODEL` e `EVAL_MODEL` para `gemini-2.5-flash`, que devolve texto.

Na iteração #2, o F1-Score foi a métrica mais baixa (0.85). Pelo tracing e pelo comentário do avaliador, os casos piores não tinham problema de precisão, e sim de **recall**: a regra "seja conciso, não adicione seções" deixava o modelo econômico demais. Faltavam critérios de acessibilidade no bug do modal, "Critérios Técnicos" nos bugs que já apontavam a causa (paginação, thread em background), "Critérios de Prevenção" no bug de estoque, "Métricas de Sucesso" nos bugs complexos, e a persona saía genérica ("usuário" em vez de "administrador" no dashboard).

| Iteração | O que mudou no prompt | Helpfulness | Correctness | F1 | Clarity | Precision |
|---|---|---|---|---|---|---|
| v2 #3 (gemini-2.5-flash) | Separar "não inventar fatos" de "completar com boas práticas"; passo de CoT sobre o que um PM exigiria; seções condicionais (Critérios Técnicos, Acessibilidade, Prevenção); Métricas de Sucesso nos complexos; persona por quem usa a funcionalidade; exemplos few-shot atualizados | 0.95 | 0.93 | **0.89** | 0.94 | 0.97 |

| v2 #4 (gemini-2.5-flash) | Mesmo prompt da #3, rodada de confirmação | 0.97 | 0.93 | 0.88 | 0.96 | 0.97 |

Resultado: o F1 subiu de 0.85 para 0.89 e a Precision não caiu (0.96 → 0.97), ou seja, as adições não viraram alucinação. A Clarity caiu um pouco (0.96 → 0.94), porque as respostas ficaram mais longas, mas continua com folga.

### v1 x v2

| | v1 | v2 |
|---|---|---|
| Persona | "assistente" genérico | Product Manager sênior com conhecimento técnico |
| Variável `{bug_report}` | no system e no user | só no user prompt |
| Formato | não definido | esqueleto por complexidade (simples, médio, complexo) |
| Exemplos | nenhum | 3 exemplos (few-shot), um por complexidade |
| Raciocínio | nenhum | CoT interno em 5 passos |
| Regras | nenhuma | preservar dados, não inventar fatos, critérios testáveis |
| Casos especiais | nenhum | relato vago, vários bugs, solução sugerida, outro idioma |

---

## Como Executar

### Pré-requisitos

- Python 3.10+
- Conta no [LangSmith](https://smith.langchain.com) com API key
- Handle público do LangSmith Hub (Prompts > ⋮ > Make Public)
- API key da OpenAI **ou** do Google Gemini

### Instalação

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Preencha o `.env`: `LANGSMITH_API_KEY`, `USERNAME_LANGSMITH_HUB`, `LLM_PROVIDER`, `LLM_MODEL`, `EVAL_MODEL` e a API key do provider escolhido.

### Execução

```bash
# 1. Pull do prompt original -> prompts/bug_to_user_story_v1.yml
python src/pull_prompts.py

# 2. Testes de validação do prompt v2
pytest tests/test_prompts.py -v

# 3. Push do prompt v2 para o LangSmith Hub
python src/push_prompts.py

# 4. Avaliação (cria um experimento no LangSmith)
python src/evaluate.py
```

Para iterar: edite `prompts/bug_to_user_story_v2.yml`, rode os testes e repita os passos 3 e 4.

Para gerar o link público do dataset (rode uma vez só, porque o link muda a cada compartilhamento):

```bash
python -c "from dotenv import load_dotenv; load_dotenv(); import os; from langsmith import Client; print(Client().share_dataset(dataset_name=os.getenv('LANGSMITH_PROJECT') + '-eval')['url'])"
```

### Estrutura

```
├── prompts/
│   ├── bug_to_user_story_v1.yml   # prompt original (pull)
│   └── bug_to_user_story_v2.yml   # prompt otimizado
├── datasets/bug_to_user_story.jsonl
├── src/
│   ├── pull_prompts.py
│   ├── push_prompts.py
│   ├── evaluate.py
│   ├── metrics.py
│   └── utils.py
└── tests/test_prompts.py
```
