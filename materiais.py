# -*- coding: utf-8 -*-
"""
Catálogo de materiais (CÓDIGO SAP + DESCRIÇÃO DO PRODUTO).

Usado pelo app de lançamento para preencher a seção "Materiais Utilizados".
A fonte padrão é a aba "Materiais" da planilha Google Sheets; se não for
possível ler, usa o arquivo local catalogo_materiais.csv.
"""
import os
import unicodedata

import pandas as pd

COLUNAS_MATERIAL = ["CÓDIGO SAP", "DESCRIÇÃO DO PRODUTO"]
ARQUIVO_CATALOGO = "catalogo_materiais.csv"
ABA_MATERIAIS = "Materiais"


def normalizar_colunas(df: pd.DataFrame, colunas: list[str]) -> pd.DataFrame:
    """Garante as colunas esperadas, tolerando nomes com/sem acento."""
    def norm(c: str) -> str:
        c = unicodedata.normalize("NFD", str(c))
        c = "".join(ch for ch in c if unicodedata.category(ch) != "Mn")
        return c.lower().strip()

    mapa = {}
    for alvo in colunas:
        an = norm(alvo)
        for c in df.columns:
            cn = norm(c)
            if an in cn or cn in an:
                mapa[c] = alvo
                break
    df = df.rename(columns=mapa)
    for col in colunas:
        if col not in df.columns:
            df[col] = ""
    return df[colunas].fillna("").astype(str)


def carregar_materiais(ler_planilha=None, avisar=None) -> pd.DataFrame:
    """
    Carrega o catálogo de materiais.

    Args:
        ler_planilha: função opcional que lê uma aba da planilha (ex.: _ler_planilha_fuzzy).
        avisar: função opcional para exibir avisos (ex.: st.warning).

    Retorna um DataFrame com as colunas COLUNAS_MATERIAL.
    """
    if ler_planilha is not None:
        try:
            df = ler_planilha(ABA_MATERIAIS)
            if df is not None and not df.empty:
                return normalizar_colunas(df, COLUNAS_MATERIAL)
        except Exception as e:
            if avisar:
                avisar(f"Não foi possível ler o catálogo de materiais na planilha ({e}). Usando CSV local.")

    if os.path.exists(ARQUIVO_CATALOGO):
        df = pd.read_csv(ARQUIVO_CATALOGO, dtype=str)
        return normalizar_colunas(df, COLUNAS_MATERIAL)
    return pd.DataFrame(columns=COLUNAS_MATERIAL)
