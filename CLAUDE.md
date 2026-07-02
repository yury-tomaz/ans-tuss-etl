# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Visão geral

Pipeline ETL que extrai dados de tabelas **TUSS** (Terminologia Unificada da Saúde
Suplementar, da ANS), normaliza e valida, e popula um banco que servirá uma API de
consultas.

Fluxo do pipeline:

```
ingestão (planilhas TUSS da ANS) → normalização → validação → saída (Parquet / PostgreSQL)
```

Cada etapa é uma responsabilidade isolada. A API de consultas consome a saída; não faz
parte deste repositório de ETL.

## Stack

- **Python 3.12**
- **Polars** para manipulação de dados (não pandas)
- **uv** para dependências e execução
- **pytest** para testes
- **ruff** para lint e formatação
- **mypy** em modo `strict` para tipagem

## Comandos

```bash
uv run pytest              # roda todos os testes
uv run pytest <arquivo>::<teste>   # roda um teste específico
uv run ruff check          # lint
uv run ruff format         # formata
uv run mypy                # checagem de tipos (strict)
```

Instalar/sincronizar dependências: `uv sync`.

## Convenções de código (obrigatórias)

Estas regras não são preferências — são o padrão do projeto e devem ser seguidas em todo
código novo.

- **Funções de 4 a 20 linhas.** Se passar disso, quebre em funções nomeadas.
- **Arquivos com menos de 500 linhas.** Uma responsabilidade por módulo.
- **Nomes específicos e grepáveis.** Proibido `data`, `process`, `handler`, `utils` e
  similares genéricos. O nome deve dizer o que a coisa é/faz (ex.: `normalize_tuss_row`,
  `TussProcedure`, `parse_ans_spreadsheet`).
- **Type hints em tudo.** Sem `Any`, sem `dict` solto como estrutura de dados. Use
  `dataclass`es ou modelos tipados para representar registros e configurações.
- **Early returns.** Máximo de 2 níveis de indentação por função. Trate casos de borda no
  topo e retorne cedo em vez de aninhar.

## Testes

- **Todo módulo novo nasce com teste.** Não crie um módulo sem seu teste correspondente.
- **Nunca commitar com teste quebrado.** `uv run pytest` deve estar verde antes de qualquer
  commit.
- CI (GitHub Actions) roda testes + lint em cada push/PR.

## Commits

- **Atômicos.** Um commit = uma mudança lógica coesa. Não misture refatoração, feature e
  formatação no mesmo commit.
- **Mensagens profissionais e objetivas, sem exageros.** Descreva o que mudou e por quê,
  sem inflar. Nada de emojis ou hype.
- **Conventional Commits** no assunto: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`,
  `ci`. Assunto no imperativo e em português (ex.: `feat: normaliza códigos TUSS`).
- **Verde antes de commitar.** `ruff check`, `ruff format --check`, `mypy` e `pytest` devem
  passar.
