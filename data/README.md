# Dados

Este diretório guarda dados que **não são versionados** no git (ver `.gitignore`).
São reproduzíveis por download da fonte oficial.

## Layout

```
data/
├── raw/<versao>/      # planilhas .xlsx / .pdf originais da ANS (entrada)
└── staging/versao=<versao>/tab_<NN>.parquet   # saída tipada da normalização
```

## Origem

- **Fonte:** ANS (Agência Nacional de Saúde Suplementar), Padrão TISS —
  Terminologia Unificada da Saúde Suplementar (TUSS).
- **Versão em uso:** `202601`.
- **Portal:** gov.br/ans, seção Padrão TISS / TUSS.
  > TODO: fixar a URL exata de download da versão utilizada.

## Como repor

Baixe o pacote da versão desejada no portal da ANS e extraia em
`data/raw/<versao>/`, preservando os nomes dos arquivos. O TUSS 19 (OPME) vem
dividido em duas partes; ambas devem estar presentes.
