# 2. Transformação em Polars (ETL); staging tables só como buffer de carga

- Status: aceito
- Data: 2026-07-02

## Contexto

Avaliou-se usar a abordagem ELT (Extract–Load–Transform): carregar o dado quase
cru em staging/temporary tables no PostgreSQL e fazer a limpeza/normalização
dentro do banco, via SQL (eventualmente com dbt). A alternativa é ETL:
transformar antes de carregar, no Polars, conforme o [ADR 0001](0001-formato-de-staging-parquet.md).

Fatos que pesam na decisão:

- **A parte difícil é o parsing do `.xlsx`, não a transformação.** Pular o
  preâmbulo (cabeçalho na 3ª linha), descartar a aba `Capa`, concatenar as duas
  partes do TUSS 19, tratar 62 abas heterogêneas e preservar `Código do Termo`
  como string (zeros à esquerda) só se faz em Python. ELT não elimina o Polars —
  apenas move a limpeza para depois da carga.
- **Volume cabe em memória.** A maior tabela (TUSS 19/OPME) tem ~1M linhas; as
  demais são pequenas. O poder set-based do banco não é necessário.
- **Convenções do projeto** favorecem funções puras tipadas com pytest e mypy
  strict; regras em SQL seriam testáveis apenas via integração, exigindo um banco
  em execução.
- **62 tabelas** tenderiam a virar 62 models SQL quase-duplicados, contra um
  transform parametrizado em Python.

## Decisão

- **A transformação permanece no Polars (ETL)**, produzindo Parquet tipado como
  staging (ADR 0001). Preserva tipos e respeita as convenções de tipagem/teste.
- **Staging tables têm lugar apenas como buffer de carga**, não como motor de
  limpeza. O SQL é usado só onde é imbatível:
  - `INSERT` em massa em uma staging table seguido de `MERGE`/`ON CONFLICT` para
    **carga idempotente** na tabela final (recarregar não duplica).
  - **Constraints, índices e views** de consulta que a API servirá.

ELT como estratégia de transformação é rejeitado; adota-se **staging table +
upsert em SQL** como padrão de carga.

## Consequências

**Positivas**
- A correção do dado não fica acoplada a um PostgreSQL em execução; extração e
  transformação seguem testáveis isoladamente e idempotentes.
- Uma única lógica de transformação parametrizada cobre as 62 tabelas.
- Carga idempotente via upsert evita duplicação em recargas.

**Negativas / custos**
- A limpeza não fica inspecionável via `SELECT` no banco (fica em código Python).
- Analistas que só dominam SQL não conseguem manter as regras de transformação.

## Reavaliação

Reabrir esta decisão se: o volume deixar de caber em memória; a transformação
passar a ser dominada por joins/agregações multi-tabela pesados; ou um time
passar a manter as regras em SQL. Nesses casos, considerar dbt.

## Alternativas consideradas

- **ELT com transformação em SQL (staging tables / dbt)** — rejeitada por não
  eliminar o parsing em Python, não ser necessária pelo volume, contrariar as
  convenções de teste/tipagem e multiplicar SQL para 62 tabelas.
