# 4. Ingestão a partir de caminho local configurável (local-first)

- Status: aceito
- Data: 2026-07-02

## Contexto

O pipeline precisa localizar e ler os arquivos `.xlsx` do TUSS. Duas abordagens:
ler de um caminho local onde os arquivos já estão, ou baixar automaticamente do
portal da ANS.

## Decisão

A ingestão lê de um **caminho local configurável**, por padrão
`data/raw/<versao>/` (ex.: `data/raw/202601/`). A `versao` é parâmetro explícito
do pipeline, derivado do caminho — não inferido do conteúdo.

O **download automático da ANS é adiado** e, quando existir, será um passo
**separado e opcional** que apenas deposita arquivos em `data/raw/<versao>/`. A
extração nunca depende de rede.

## Consequências

**Positivas**
- Extração pura, determinística e testável: dado o diretório, o resultado é fixo.
- Desacopla a obtenção do dado (frágil, site da ANS muda) do processamento.
- Reprocessar não depende de disponibilidade externa.

**Negativas / custos**
- Obter e depositar os arquivos é responsabilidade externa ao pipeline por ora.

## Alternativas consideradas

- **Download automático da ANS** — rejeitada agora: acopla a rede e o layout do
  site da ANS ao ETL, é frágil e difícil de testar.
- **Híbrido (local por padrão + download opcional)** — adiada: será o passo de
  download opcional acima, quando houver necessidade.
