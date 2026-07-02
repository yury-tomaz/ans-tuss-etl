# 5. Layout do staging: um Parquet por terminologia, particionado por versão

- Status: aceito
- Data: 2026-07-02

## Contexto

Definido o Parquet como staging tipado (ADR 0001) e o versionamento por snapshot
(ADR 0003), falta o layout físico dos arquivos. A complicação é o arquivo "Demais
terminologias", que é um único workbook com 62 abas heterogêneas, e o TUSS 19
(OPME), dividido em duas partes por limite de linhas do Excel.

## Decisão

- **Um Parquet por terminologia (tabela TUSS)**, não por arquivo de origem nem
  agregado.
- **Particionamento por versão** no caminho, estilo Hive:
  `data/staging/versao=<versao>/tab_<NN>.parquet` (ex.:
  `data/staging/versao=202601/tab_22.parquet`).
- As **62 abas** de "Demais terminologias" viram **um Parquet cada** (uma por
  terminologia), seguindo a mesma convenção. Abas meta/índice (ex.: Tab 87 - Lista
  de terminologias) não geram Parquet de dados.
- As **duas partes do TUSS 19 (OPME)** são **concatenadas** em um único
  `tab_19.parquet`.

## Consequências

**Positivas**
- Um arquivo por terminologia lógica, independente de como a ANS empacotou.
- Partição por versão torna carga e recarga por release simples e idempotentes.
- Schema homogêneo dentro de cada Parquet (uma terminologia = um schema).

**Negativas / custos**
- Muitos arquivos pequenos (as terminologias da cauda longa são minúsculas).

## Alternativas consideradas

- **Um Parquet por arquivo de origem** — rejeitada: "Demais terminologias"
  agruparia 62 schemas diferentes em um só arquivo.
- **Um Parquet único agregando tudo** — rejeitada: mistura schemas heterogêneos e
  impede evolução por terminologia.
