# -*- coding: utf-8 -*-
"""
Catálogo de materiais (CÓDIGO SAP + DESCRIÇÃO DO PRODUTO).

Usado pelo app de lançamento para preencher a seção "Materiais Utilizados".
A fonte padrão é o arquivo local catalogo_materiais.csv; se não for
possível ler, usa a aba "Materiais" da planilha Google Sheets.
"""
import os
import unicodedata

import pandas as pd

COLUNAS_MATERIAL = ["CÓDIGO SAP", "DESCRIÇÃO DO PRODUTO"]
ARQUIVO_CATALOGO = os.path.join(os.path.dirname(__file__), "catalogo_materiais.csv")
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
    Carrega o catálogo local primeiro e usa a planilha como fallback.

    Args:
        ler_planilha: função opcional que lê uma aba da planilha (ex.: _ler_planilha_fuzzy).
        avisar: função opcional para exibir avisos (ex.: st.warning).

    Retorna um DataFrame com as colunas COLUNAS_MATERIAL.
    """
    erro_csv = None
    if os.path.exists(ARQUIVO_CATALOGO):
        try:
            df = pd.read_csv(ARQUIVO_CATALOGO, dtype=str)
            if not df.empty:
                return normalizar_colunas(df, COLUNAS_MATERIAL)
            erro_csv = ValueError("o arquivo está vazio")
            if avisar:
                avisar("O catálogo CSV está vazio. Tentando a planilha Google.")
        except Exception as e:
            erro_csv = e
            if avisar:
                avisar(f"Não foi possível ler o catálogo CSV ({e}). Tentando a planilha Google.")

    erro_planilha = None
    if ler_planilha is not None:
        try:
            df = ler_planilha(ABA_MATERIAIS)
            if df is not None and not df.empty:
                return normalizar_colunas(df, COLUNAS_MATERIAL)
        except Exception as e:
            erro_planilha = e
            if avisar:
                avisar(f"Não foi possível ler o catálogo na planilha Google ({e}).")

    if erro_csv is not None or erro_planilha is not None:
        detalhes = []
        if erro_csv is not None:
            detalhes.append(f"CSV: {erro_csv}")
        if erro_planilha is not None:
            detalhes.append(f"planilha Google: {erro_planilha}")
        erro_origem = erro_planilha or erro_csv
        raise RuntimeError(f"Não foi possível carregar o catálogo ({'; '.join(detalhes)}).") from erro_origem
    raise FileNotFoundError(f"Catálogo CSV não encontrado e a planilha Google não está disponível: {ARQUIVO_CATALOGO}")
