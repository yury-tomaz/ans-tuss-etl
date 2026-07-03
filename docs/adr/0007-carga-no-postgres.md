# 7. Carga no PostgreSQL: COPY + upsert por row_hash, migrations com golang-migrate

- Status: aceito
- Data: 2026-07-03

## Contexto

O staging produz Parquet tipado por versão (ADR 0001/0005): núcleo em
`tab_<NN>.parquet` e extensões ricas em `ext_medicamento.parquet` /
`ext_opme.parquet`. Falta carregar esse staging no PostgreSQL que servirá a API
de consultas, de forma **idempotente** (recarregar a mesma versão não duplica
nem reescreve linha inalterada), conforme o padrão de carga do [ADR 0002](0002-transformacao-em-polars-nao-elt.md).

Três decisões precisavam ser fixadas: como carregar, como versionar o schema e
como rodar o banco localmente.

## Decisão

### Estratégia de carga: COPY para staging table + upsert por `row_hash`

Para cada Parquet, o loader (psycopg + `COPY`):

1. `COPY` das linhas do Parquet para uma **staging table temporária** com o mesmo
   schema da tabela de destino (`CREATE TEMP TABLE ... ON COMMIT DROP`).
2. `INSERT ... SELECT ... ON CONFLICT (versao, tabela, codigo) DO UPDATE`
   condicionado a `WHERE destino.row_hash IS DISTINCT FROM excluded.row_hash`.

Assim `row_hash` (ADR 0003) faz o CDC: só linha nova ou de conteúdo alterado é
escrita; recarga da mesma versão é no-op. É a "staging table como buffer de
carga" prevista no ADR 0002 — não como motor de limpeza.

### Schema físico

Chave primária `(versao, tabela, codigo)` no núcleo `tuss_termo` e nas extensões
`tuss_medicamento` / `tuss_opme`, com FK das extensões para o núcleo por
`(versao, tabela, codigo)`. Isto **refina** o ADR 0006, que previa a FK por
`(versao, codigo)`: `codigo` só é único dentro de uma tabela, então a chave
completa inclui `tabela`. O Parquet de extensão já carrega as três colunas.

### Migrations: golang-migrate

O schema é versionado com **golang-migrate**, em SQL puro (`NNNN_nome.up.sql` /
`.down.sql`), com a versão rastreada na tabela `schema_migrations`. O binário é
pinado no `mise.toml`, então o mesmo `jdx/mise-action` que já provê python/uv o
instala no CI sem passo extra. Fica fora do processo Python: o loader assume o
schema já migrado.

### Infra local: Docker Compose

Um serviço PostgreSQL em `docker-compose.yml` para desenvolvimento e para os
testes de integração do loader.

## Consequências

**Positivas**
- Recarga idempotente e barata: `row_hash` evita reescrever linha inalterada.
- SQL usado só onde é imbatível (bulk `COPY` + upsert), coerente com o ADR 0002.
- Migrations em SQL puro, versionadas e auditáveis, com a ferramenta já pinada no
  toolchain via mise.
- Schema desacoplado do código de carga: migrar e carregar são passos separados.

**Negativas / custos**
- O teste do loader exige um PostgreSQL em execução (Docker Compose), diferente
  dos testes puros das etapas anteriores.
- Um binário não-Python (`migrate`) entra no toolchain — mitigado por já usarmos
  mise para pinar ferramentas.

## Alternativas consideradas

- **Alembic** — rejeitada: seu forte é acoplado ao SQLAlchemy ORM, que não usamos
  (escrita é Polars + psycopg). Traria SQLAlchemy só para migrar, sem ganho.
- **yoyo-migrations** — alternativa pure-Python viável (SQL puro, instala via uv),
  descartada por preferência pela ferramenta já dominada (`migrate`), que o mise
  provê sem fricção.
- **`INSERT` linha a linha / upsert sem staging** — rejeitada: ordens de magnitude
  mais lento que `COPY` na maior tabela (OPME, ~1,4M linhas).
