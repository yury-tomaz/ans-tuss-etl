# etl-tuss

Pipeline ETL que extrai as tabelas **TUSS** (Terminologia Unificada da Saúde
Suplementar, da ANS), normaliza e valida, e popula um banco PostgreSQL que serve
uma API de consultas. A API não faz parte deste repositório.

## Visão geral

```
planilhas TUSS da ANS → normalização → Parquet (staging) → PostgreSQL
```

O pipeline lê os `.xlsx` de um release da ANS, normaliza para um schema tipado,
grava um staging em Parquet particionado por versão (`versao=<v>/`) e carrega no
PostgreSQL. A carga é idempotente: recarregar uma versão atualiza apenas o que
mudou, e versões diferentes coexistem no banco.

## Stack

- Python 3.12 · [Polars](https://pola.rs) · [uv](https://docs.astral.sh/uv/)
- PostgreSQL 16 · [golang-migrate](https://github.com/golang-migrate/migrate)
- Toolchain gerenciado por [mise](https://mise.jdx.dev)
- pytest · ruff · mypy (modo `strict`)

## Pré-requisitos

- [mise](https://mise.jdx.dev) (provê Python, uv e o binário `migrate`)
- Docker + Docker Compose (PostgreSQL local)

## Setup

```bash
# 1. Ferramentas (python, uv, migrate) e dependências
mise install
uv sync

# 2. Banco de dados local
docker-compose up -d

# 3. Schema (uma vez por banco novo)
mise exec -- migrate -path migrations \
  -database "postgres://tuss:tuss@localhost:5432/tuss?sslmode=disable" up
```

## Uso

O pipeline completo (extração + carga) roda em um comando:

```bash
uv run etl-tuss <diretório-do-release> <versao>
```

Exemplo com o release baixado em `data/raw/202601`:

```bash
uv run etl-tuss data/raw/202601 202601
```

Saída:

```
versao=202601 carregada:
  termo: 1442987 inseridas, 0 atualizadas, 0 inalteradas
  medicamento: 43376 inseridas, 0 atualizadas, 0 inalteradas
  opme: 1388442 inseridas, 0 atualizadas, 0 inalteradas
```

**Argumentos e opções:**

| Argumento          | Descrição                                                        |
| ------------------ | ---------------------------------------------------------------- |
| `release_dir`      | diretório com os `.xlsx` do release da ANS                       |
| `versao`           | rótulo do release (padrão recomendado `AAAAMM`, ex.: `202601`)   |
| `--staging <dir>`  | raiz do staging Parquet (padrão: `./staging`)                    |
| `--dsn <dsn>`      | DSN do PostgreSQL (padrão: env `TUSS_DSN` ou o compose local)    |

O comando não aplica migrations; garanta o schema criado (passo 3 do Setup)
antes de carregar.

## Modelo de dados

| Tabela             | Conteúdo                                                        |
| ------------------ | -------------------------------------------------------------- |
| `tuss_termo`       | código, termo, descrição e datas de vigência                   |
| `tuss_medicamento` | atributos da Tab 20: apresentação, laboratório, registro ANVISA |
| `tuss_opme`        | atributos da Tab 19: modelo, fabricante, classe de risco, etc. |

Todas têm chave `(versao, tabela, codigo)`; `tuss_medicamento` e `tuss_opme`
referenciam `tuss_termo` por essa chave.

Exemplos de consulta:

```sql
-- volume por tabela
SELECT tabela, count(*) FROM tuss_termo GROUP BY tabela ORDER BY 2 DESC;

-- núcleo + extensão de medicamento
SELECT t.codigo, t.termo, m.apresentacao, m.laboratorio
FROM tuss_termo t
JOIN tuss_medicamento m USING (versao, tabela, codigo)
LIMIT 20;

-- procedimentos (Tab 22) ainda vigentes
SELECT codigo, termo FROM tuss_termo
WHERE tabela = '22' AND fim_vigencia IS NULL;
```

## Estrutura do projeto

```
src/etl_tuss/   # módulos do pipeline (extração, normalização, carga, CLI)
migrations/     # migrations SQL (golang-migrate)
docs/adr/       # decisões de arquitetura
data/           # dados não versionados (ver data/README.md)
```

## Desenvolvimento

```bash
uv run pytest          # roda os testes
uv run ruff check      # lint
uv run ruff format     # formata
uv run mypy            # checagem de tipos (strict)
```

Os testes de integração exigem o PostgreSQL de pé; quando o banco está
indisponível, são pulados. Eles recriam o schema do banco, então rodá-los apaga
dados carregados — basta repopular com o CLI.

### Migrations

```bash
# aplicar / reverter
mise exec -- migrate -path migrations -database "$DSN" up
mise exec -- migrate -path migrations -database "$DSN" down -all

# criar uma nova migration
mise exec -- migrate create -ext sql -dir migrations -seq <nome>
```

## Dados

Os dados não são versionados no git; são reproduzíveis por download da ANS. Ver
[`data/README.md`](data/README.md) para origem e layout.

## Arquitetura

As decisões de arquitetura estão registradas em [`docs/adr/`](docs/adr/).
