# 3. Versionamento por snapshot com `versao` de primeira classe e `row_hash`

- Status: aceito
- Data: 2026-07-02

## Contexto

O TUSS é publicado pela ANS em releases datados (ex.: `202601`). É preciso decidir
como o pipeline lida com múltiplas versões: ingerir novos releases quando saem e,
eventualmente, popular releases anteriores. A necessidade foi avaliada pelos dois
personas que consultam a API.

- **Profissional de saúde / faturamento (prospectivo):** atribui código a um
  procedimento *hoje*. Precisa do release mais recente + vigência atual. Não exige
  histórico multi-release.
- **Auditoria (retrospectivo):** julga uma conta submetida no passado pelo código
  que valia *naquela data*. É inerentemente point-in-time.

Existem duas noções distintas de tempo, que não devem ser colapsadas:

1. **Vigência** (valid-time) — colunas de origem `Data de início/fim de vigência`.
2. **Versão do release** (transaction-time / as-published) — metadado que anexamos.

### Achado nos dados que orienta a decisão

Inspeção dos arquivos 202601:

- Os arquivos **são cumulativos**: retêm códigos introduzidos anos antes (início de
  vigência em 2009 na Tab 22).
- Porém `Data de fim de vigência` é **quase sempre vazia** — observado 0,0% (Tab 22,
  Tab 20) e 0,1% (Tab 18) das linhas preenchidas.

Consequência: a vigência fornece o **início** confiável, mas **raramente o fim**.
Sozinha, ela **não reconstrói** de forma fiel "o código estava vigente em D".
Descontinuações e alterações entre releases só se detectam **comparando releases**.

## Decisão

Adotar **versionamento por snapshot**, com estes três elementos desde já:

1. **`versao` como dimensão de primeira classe** — parâmetro explícito do pipeline
   (derivado do caminho `data/raw/<versao>/`, não inferido), presente no layout de
   raw, no Parquet particionado (`staging/versao=<versao>/<tabela>.parquet`) e como
   coluna nas tabelas do banco. Popular qualquer versão, passada ou futura, é
   idempotente e independente de ordem.
2. **Snapshot completo por release** — cada versão é um conjunto independente e
   reproduzível. O custo é baixo (dado pequeno, Parquet comprime).
3. **`row_hash`** — hash determinístico sobre as colunas de conteúdo, com chave
   natural `(tabela, código do termo)`. Habilita upsert idempotente (recarregar a
   mesma versão é no-op) e o **diff entre releases** (adicionados / removidos /
   alterados) — o mecanismo principal de reconstrução histórica para auditoria,
   dado que a vigência não marca o fim.

O hash deve ser determinístico: normalizar antes de hashear (trim, tratamento de
null consistente, ordem de colunas estável, encoding fixo) para evitar falsos diffs.

### Escopo — o que fica adiado (YAGNI)

- **SCD Type 2 / API point-in-time "as-published"** — só quando um requisito
  concreto de auditoria exigir reconstruir a tabela como publicada numa data. A
  capacidade é habilitada agora (snapshots + hash) sem construir a máquina.
- **Carregar releases anteriores ao inicial** — suportado pela arquitetura, feito
  apenas quando houver necessidade real.

## Consequências

**Positivas**
- Auditoria retrospectiva viável: diff entre releases reconstrói mudanças que a
  vigência não registra.
- Popular qualquer versão é idempotente e sem ordem imposta.
- Proveniência (`versao`) em cada linha.

**Negativas / custos**
- Armazenamento redundante entre releases (mitigado pelo tamanho pequeno e Parquet).
- Determinismo do hash exige normalização cuidadosa, senão gera falsos diffs.

## Alternativas consideradas

- **Só o release mais recente (overwrite)** — rejeitada: impede auditoria
  retrospectiva.
- **SCD Type 2 já** — adiada: sem requisito concreto de point-in-time as-published,
  seria over-engineering.
- **Confiar só na vigência para point-in-time** — insuficiente: `fim de vigência`
  quase sempre vazio não reconstrói o fim de validade.
