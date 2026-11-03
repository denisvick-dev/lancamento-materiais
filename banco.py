# -*- coding: utf-8 -*-
"""
Banco de dados local (SQLite) com os lançamentos de materiais.

O arquivo do banco fica em dados/lancamentos.db (fora do versionamento).
A tabela "lancamentos" usa as mesmas colunas do app (COLUNAS do streamlit_app).
"""

import os
import sqlite3

import pandas as pd

PASTA_DADOS = "dados"
ARQUIVO_BANCO = os.path.join(PASTA_DADOS, "lancamentos.db")
TABELA = "lancamentos"


def _conectar() -> sqlite3.Connection:
    os.makedirs(PASTA_DADOS, exist_ok=True)
    conn = sqlite3.connect(ARQUIVO_BANCO)
    return conn


def criar_tabela(colunas: list[str]) -> None:
    """Cria a tabela se não existir (todas as colunas como TEXT)."""
    cols_sql = ", ".join(f'"{c}" TEXT' for c in colunas)
    with _conectar() as conn:
        conn.execute(
            f"CREATE TABLE IF NOT EXISTS {TABELA} (id INTEGER PRIMARY KEY AUTOINCREMENT, {cols_sql})"
        )


def listar(colunas: list[str]) -> pd.DataFrame:
    """Retorna todos os lançamentos como DataFrame."""
    criar_tabela(colunas)
    with _conectar() as conn:
        df = pd.read_sql_query(f"SELECT {', '.join(colunas)} FROM {TABELA}", conn)
    for col in colunas:
        if col not in df.columns:
            df[col] = ""
    return df[colunas].fillna("")


def salvar_tudo(df: pd.DataFrame, colunas: list[str]) -> None:
    """Substitui todo o conteúdo da tabela pelo DataFrame informado."""
    criar_tabela(colunas)
    df = df[colunas].fillna("").astype(str)
    with _conectar() as conn:
        conn.execute(f"DELETE FROM {TABELA}")
        placeholders = ", ".join("?" for _ in colunas)
        conn.executemany(
            f"INSERT INTO {TABELA} ({', '.join(colunas)}) VALUES ({placeholders})",
            df.values.tolist(),
        )


def inserir(linha: dict, colunas: list[str]) -> None:
    """Insere um único lançamento."""
    criar_tabela(colunas)
    valores = [str(linha.get(c, "")) for c in colunas]
    placeholders = ", ".join("?" for _ in colunas)
    with _conectar() as conn:
        conn.execute(
            f"INSERT INTO {TABELA} ({', '.join(colunas)}) VALUES ({placeholders})",
            valores,
        )


def excluir(ids: list[int]) -> None:
    """Exclui lançamentos pelos ids."""
    if not ids:
        return
    with _conectar() as conn:
        conn.executemany(f"DELETE FROM {TABELA} WHERE id = ?", [(i,) for i in ids])
