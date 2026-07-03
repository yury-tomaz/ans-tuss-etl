CREATE TABLE tuss_termo (
    versao          text NOT NULL,
    tabela          text NOT NULL,
    codigo          text NOT NULL,
    termo           text NOT NULL,
    descricao       text,
    inicio_vigencia date,
    fim_vigencia    date,
    fim_implantacao date,
    row_hash        text NOT NULL,
    PRIMARY KEY (versao, tabela, codigo)
);

CREATE TABLE tuss_medicamento (
    versao          text NOT NULL,
    tabela          text NOT NULL,
    codigo          text NOT NULL,
    apresentacao    text,
    laboratorio     text,
    registro_anvisa text,
    row_hash        text NOT NULL,
    PRIMARY KEY (versao, tabela, codigo),
    FOREIGN KEY (versao, tabela, codigo)
        REFERENCES tuss_termo (versao, tabela, codigo) ON DELETE CASCADE
);

CREATE TABLE tuss_opme (
    versao          text NOT NULL,
    tabela          text NOT NULL,
    codigo          text NOT NULL,
    modelo          text,
    fabricante      text,
    registro_anvisa text,
    classe_risco    text,
    nome_tecnico    text,
    row_hash        text NOT NULL,
    PRIMARY KEY (versao, tabela, codigo),
    FOREIGN KEY (versao, tabela, codigo)
        REFERENCES tuss_termo (versao, tabela, codigo) ON DELETE CASCADE
);
