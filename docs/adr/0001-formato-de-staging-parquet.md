# 1. Parquet como camada de staging entre extração e carga

- Status: aceito
- Data: 2026-07-02

## Contexto

O pipeline extrai tabelas TUSS de planilhas `.xlsx` da ANS, normaliza/valida e
carrega em um banco (PostgreSQL) que servirá uma API de consultas. Surgiu a
questão: converter primeiro `xlsx → CSV` e então inserir, ou carregar direto?

A inspeção das planilhas revelou características que pesam na decisão:

- **`Código do Termo` é identificador, não número.** Há códigos de um dígito
  (`"1"`, `"2"`), de 8 dígitos e tabelas com zeros à esquerda. Precisa permanecer
  string; re-inferência de tipo o corromperia.
- **Datas já vêm tipadas** (`datetime`) pelas planilhas.
- **Schema varia por tabela** — de 5 a 8 colunas — e o arquivo "Demais
  terminologias" é um único workbook com **62 abas** heterogêneas (Tab 23→87).
- **Layout com preâmbulo**: aba `Capa` vazia + cabeçalho real na 3ª linha.
- **Volume alto e fragmentado**: TUSS 19 (OPME) tem 76MB + 34MB, dividido em duas
  partes por causa do limite de linhas do Excel.

O parsing de `.xlsx` é a etapa lenta e frágil; a carga no banco é separada e
falível de forma independente.

## Decisão

Usamos **Parquet como camada intermediária tipada** entre extração e carga:

```
xlsx → normalização (Polars) → Parquet tipado (staging) → carga no PostgreSQL
```

- **CSV como intermediário é rejeitado**: perde tipos, transformando
  identificadores com zero à esquerda em números ambíguos e datas em texto de
  locale ambíguo; ainda fragmenta o workbook de 62 abas em 62 arquivos e é frágil
  com vírgula/acento/quebra de linha em campos livres.
- **Carga direta (xlsx → PostgreSQL) é rejeitada**: acopla o parsing frágil/lento
  à carga, força re-parsear tudo a cada falha de banco, dificulta testar a
  normalização isoladamente e não é idempotente.

Se a carga no PostgreSQL exigir `COPY` bruto por desempenho, o CSV é gerado
**apenas no último passo de load**, a partir de um frame já validado. Isso é
detalhe de carga, não o formato de staging.

## Consequências

**Positivas**
- Schema e tipos viajam com os dados: o que é extraído é exatamente o que é
  carregado (código = string, data = date).
- Formato colunar e comprimido reduz drasticamente o footprint em disco frente
  aos `.xlsx` originais.
- Staging inspecionável e re-carregável sem re-parsear as planilhas; extração e
  carga tornam-se independentemente testáveis e idempotentes.
- Alinha-se à arquitetura já declarada ("saída em Parquet/PostgreSQL").

**Negativas / custos**
- Parquet é binário — não abre diretamente no Excel para inspeção manual.
- Adiciona uma dependência de escrita/leitura de Parquet e um artefato
  intermediário a gerenciar no ciclo do pipeline.

## Alternativas consideradas

- **CSV como intermediário** — rejeitada por perda de tipo em identificadores.
- **Carga direta xlsx → PostgreSQL** — rejeitada por acoplar parsing e carga.
