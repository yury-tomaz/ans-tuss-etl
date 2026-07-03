# etl-tuss

Pipeline ETL que extrai as tabelas **TUSS** (Terminologia Unificada da Saúde
Suplementar, da ANS), normaliza e valida, e popula um banco PostgreSQL que serve
uma API de consultas. A API não faz parte deste repositório.

## Visão geral

```
ingestão (planilhas TUSS da ANS) → normalização → Parquet (staging) → PostgreSQL
```

- A transformação acontece em **Polars** (ETL), não em SQL. O SQL entra só na
  carga: `COPY` para uma tabela temporária e upsert idempotente.
- O staging intermediário é **Parquet tipado**, particionado por versão do
  release (`versao=<v>/`).
- A carga é **idempotente e versionada por snapshot**: recarregar a mesma versão
  não duplica nem reescreve linha inalterada; versões diferentes coexistem no
  banco.

As decisões de arquitetura estão registradas em [`docs/adr/`](docs/adr/).

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

Ao recarregar, `inseridas`/`atualizadas` refletem só o que mudou desde a última
carga (comparação por hash de conteúdo); o resto conta como `inalteradas`.

**Argumentos e opções:**

| Argumento          | Descrição                                                        |
| ------------------ | ---------------------------------------------------------------- |
| `release_dir`      | diretório com os `.xlsx` do release da ANS                       |
| `versao`           | rótulo do release (padrão recomendado `AAAAMM`, ex.: `202601`)   |
| `--staging <dir>`  | raiz do staging Parquet (padrão: `./staging`)                    |
| `--dsn <dsn>`      | DSN do PostgreSQL (padrão: env `TUSS_DSN` ou o compose local)    |

O comando **não** migra o schema — isso é um passo separado (ver Setup e o
[ADR 0007](docs/adr/0007-carga-no-postgres.md)).

## Modelo de dados

Modelo **híbrido** (ver [ADR 0006](docs/adr/0006-modelo-de-dados-hibrido.md)):
um núcleo unificado cobre a maioria das terminologias, e tabelas de extensão
guardam os atributos ricos.

| Tabela             | Conteúdo                                                       |
| ------------------ | ------------------------------------------------------------- |
| `tuss_termo`       | núcleo: código, termo, descrição e datas de vigência          |
| `tuss_medicamento` | extensão da Tab 20: apresentação, laboratório, registro ANVISA |
| `tuss_opme`        | extensão da Tab 19: modelo, fabricante, classe de risco, etc. |

Chave `(versao, tabela, codigo)` em todas; as extensões referenciam o núcleo por
FK na mesma chave.

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
src/etl_tuss/
├── sheet_reader.py           # lê a aba de dados, pula preâmbulo, aplica cabeçalho
├── tuss_schema.py            # normaliza o núcleo (rótulos → campos canônicos)
├── medicamento_schema.py     # normaliza a extensão de medicamentos (Tab 20)
├── opme_schema.py            # normaliza a extensão de OPME (Tab 19)
├── content_hash.py           # row_hash SHA-256 para CDC/upsert
├── terminology_assembler.py  # monta o núcleo de uma aba (+ versao/tabela/hash)
├── extension_assembler.py    # monta as extensões ricas
├── parquet_writer.py         # escrita atômica do staging em Parquet
├── release_sources.py        # descobre as fontes de um release por convenção
├── release_extractor.py      # orquestra a extração do release → staging
├── postgres_loader.py        # COPY + upsert idempotente por row_hash
├── release_loader.py         # carrega o staging inteiro em ordem segura de FK
└── cli.py                    # entrypoint: extrai + carrega
migrations/                   # migrations SQL (golang-migrate)
docs/adr/                     # decisões de arquitetura
data/                         # dados não versionados (ver data/README.md)
```

## Desenvolvimento

```bash
uv run pytest          # roda os testes
uv run ruff check      # lint
uv run ruff format     # formata
uv run mypy            # checagem de tipos (strict)
```

Testes de integração exigem o PostgreSQL de pé; quando o banco está indisponível,
eles são **pulados** (a suíte segue verde). Eles recriam o schema do banco de
teste, então rodá-los apaga dados carregados no mesmo banco — basta repopular com
o CLI.

### Migrations

```bash
# aplicar / reverter tudo
mise exec -- migrate -path migrations -database "$DSN" up
mise exec -- migrate -path migrations -database "$DSN" down -all

# criar uma nova migration
mise exec -- migrate create -ext sql -dir migrations -seq <nome>
```

## Dados

Os dados não são versionados no git; são reproduzíveis por download da ANS. Ver
[`data/README.md`](data/README.md) para origem e layout.
