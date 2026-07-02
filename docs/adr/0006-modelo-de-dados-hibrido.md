# 6. Modelo de dados: núcleo unificado + extensões para terminologias ricas

- Status: aceito
- Data: 2026-07-02

## Contexto

Os schemas das terminologias TUSS variam (5 a 8 colunas). Era preciso decidir entre
modelar cada terminologia como sua própria tabela física (por causa de possíveis
regras de negócio) ou usar um modelo unificado.

### Evidência empírica (release 202601)

Varredura das 60 abas de "Demais terminologias":

- **54 abas** têm o **mesmo núcleo idêntico**: `Código do Termo`, `Termo`, e as três
  datas de vigência.
- **4 abas** têm apenas **uma coluna extra** (Tab 59 `Sigla`; Tab 60/79 `Descrição
  Detalhada`; Tab 81 uma flag booleana).
- 2 abas são meta/índice (sem tabela de dados).

Arquivos avulsos: Tab 18/22 = núcleo + `Descrição Detalhada`; **Tab 20
(Medicamentos)** = núcleo + `Apresentação`, `Laboratório`, `Registro Anvisa`; **Tab
19 (OPME)** = núcleo + `Modelo`, `Fabricante`, `Registro Anvisa`, `Classe de Risco`,
`Nome Técnico`.

Ou seja, ~90% das terminologias têm forma idêntica; só medicamentos e OPME são
genuinamente ricas.

## Decisão

Modelo **híbrido**, dirigido pela evidência:

1. **Tabela núcleo `tuss_termo`** — chave primária `(versao, tabela, codigo)`,
   colunas comuns (`termo`, `descricao` nullable, três datas de vigência) e
   `row_hash`. Cobre integralmente as ~56 terminologias de forma uniforme; a API
   tem um único caminho de lookup por `(tabela, codigo)`.
2. **Tabelas de extensão dedicadas** apenas para as terminologias ricas, 1:1 com o
   núcleo via `(versao, codigo)`, com colunas tipadas e constraints:
   - `tuss_medicamento` (Tab 20): `apresentacao`, `laboratorio`, `registro_anvisa`.
   - `tuss_opme` (Tab 19): `modelo`, `fabricante`, `registro_anvisa`,
     `classe_risco`, `nome_tecnico`.
3. **Cauda longa** (colunas extras isoladas como `Sigla` na Tab 59 ou a flag na Tab
   81) → coluna `atributos` JSONB no núcleo, ou omitida se a API não precisar. Não
   justifica tabela própria.
4. **Regras de negócio por terminologia** vivem em **modelos tipados no Python**
   (dataclasses/validadores por tabela), na validação e no serving — não no schema
   físico. Assim há regra por tabela sem 56 tabelas físicas.

## Consequências

**Positivas**
- Um caminho de consulta uniforme e indexado para a grande maioria das
  terminologias.
- Medicamentos e OPME modelados com tipos e constraints reais, onde as regras de
  negócio importam.
- Evita a explosão de ~56 tabelas físicas idênticas; alinha com o transform
  parametrizado (ADR 0002).
- Evolutivo: uma terminologia que ganhe consultas distintas pode ser promovida a
  extensão própria.

**Negativas / custos**
- Separar modelo lógico (por tabela, no Python) de armazenamento físico (núcleo +
  extensões) exige disciplina para manter os dois coerentes.
- Cauda longa em JSONB tem tipagem/constraint mais fracas que colunas dedicadas.

## Alternativas consideradas

- **Uma tabela física por terminologia** — rejeitada: ~56 tabelas de schema
  idêntico, redundância sem benefício, 56 caminhos de API para um único tipo de
  lookup.
- **Tabela única EAV / só JSON** — rejeitada: perde tipagem e constraints
  justamente nas terminologias ricas (medicamentos, OPME).
