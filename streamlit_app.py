# -*- coding: utf-8 -*-
"""
Lançamento de Materiais — Contratos Fora TOA
Sistema para inserir e consultar os materiais lançados por contrato/WO.
"""

from io import BytesIO
import os
from datetime import date

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Configuração da página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Lançamento de Materiais — Fora TOA",
    page_icon="📦",
    layout="wide",
)

ARQUIVO_LOCAL = os.path.join("dados", "lancamentos.csv")
ARQUIVO_ATIVOS = os.path.join("dados", "ativos.csv")

# Planilha Google Sheets com a lista de ativos (técnicos) e os lançamentos
SPREADSHEET_ID = "1LQKDcLshC6XSXLBVWaEYSpxrro6uydyU9pwDLc38pEg"
ABA_LANCAMENTOS = "Lançamentos"
ABA_ATIVOS = "Ativos"

COLUNAS = [
    "Data",
    "Contrato",
    "WO",
    "Login p/ Inserir material",
    "RE",
    "Técnico",
    "CÓDIGO SAP",
    "DESCRIÇÃO DO PRODUTO",
    "UM.",
    "QUANTIDADE",
]

UNIDADES = ["UN.", "M", "M²", "M³", "CX", "PC", "KG", "L", "RL"]


# ---------------------------------------------------------------------------
# Camada de persistência (Google Sheets se configurado, senão CSV local)
# ---------------------------------------------------------------------------
def _planilha_configurada() -> bool:
    """True se houver conta de serviço do Google configurada em st.secrets."""
    try:
        return bool(st.secrets.get("gcp_service_account", {}).get("client_email"))
    except Exception:
        return False


def _spreadsheet_id() -> str:
    try:
        return st.secrets.get("gsheets", {}).get("spreadsheet") or SPREADSHEET_ID
    except Exception:
        return SPREADSHEET_ID


def _conexao_planilha():
    from streamlit_gsheets.gsheets_connection import GSheetsServiceAccountClient

    spreadsheet = _spreadsheet_id()
    if "://" not in spreadsheet:
        spreadsheet = f"https://docs.google.com/spreadsheets/d/{spreadsheet}/edit"

    credenciais = dict(st.secrets["gcp_service_account"])
    credenciais["spreadsheet"] = spreadsheet
    return GSheetsServiceAccountClient(credenciais)


def _ler_planilha(worksheet: str | int, ttl: int = 300) -> pd.DataFrame | None:
    """Lê uma aba da planilha Google; retorna None se falhar."""
    df = _conexao_planilha().read(worksheet=worksheet, ttl=ttl)
    if df is None or df.empty:
        return None
    return df


def _normalizar_colunas(df: pd.DataFrame, colunas: list[str]) -> pd.DataFrame:
    """Garante que o DataFrame tenha as colunas esperadas (nomes normalizados)."""
    import unicodedata

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


def _normalizar_re(valor: object) -> str:
    re = str(valor).strip()
    if re.endswith(".0") and re[:-2].isdigit():
        return re[:-2]
    return re


@st.cache_data(ttl=300, show_spinner=False)
def carregar_ativos() -> pd.DataFrame:
    """Carrega a lista de ativos (login, técnico e RE) da planilha Google."""
    colunas = ["Login", "Técnico", "RE"]
    if _planilha_configurada():
        try:
            from gspread.exceptions import WorksheetNotFound

            aba = ABA_ATIVOS
            try:
                aba = st.secrets["gsheets"].get("ativos_worksheet", ABA_ATIVOS)
            except Exception:
                pass
            try:
                df = _ler_planilha(aba)
            except WorksheetNotFound:
                df = None
            if df is None:  # tenta a primeira aba caso "Ativos" não exista
                df = _ler_planilha(0)
            if df is not None:
                return _normalizar_colunas(df, colunas)
        except Exception as e:
            st.warning(f"Não foi possível ler a lista de ativos na planilha ({e}). Usando arquivo local.")

    if os.path.exists(ARQUIVO_ATIVOS):
        df = pd.read_csv(ARQUIVO_ATIVOS, dtype=str)
        return _normalizar_colunas(df, colunas)
    return pd.DataFrame(columns=colunas)


def carregar_dados() -> pd.DataFrame:
    """Carrega os lançamentos registrados."""
    if _planilha_configurada():
        try:
            aba = ABA_LANCAMENTOS
            try:
                aba = st.secrets["gsheets"].get("worksheet", ABA_LANCAMENTOS)
            except Exception:
                pass
            df = _ler_planilha(aba)
            if df is not None:
                return _normalizar_colunas(df, COLUNAS)
        except Exception as e:
            st.warning(f"Não foi possível ler a planilha ({e}). Usando arquivo local.")

    if os.path.exists(ARQUIVO_LOCAL):
        df = pd.read_csv(ARQUIVO_LOCAL, dtype=str)
        return _normalizar_colunas(df, COLUNAS)
    return pd.DataFrame(columns=COLUNAS)


def salvar_dados(df: pd.DataFrame) -> None:
    """Persiste o DataFrame completo."""
    df = df[COLUNAS]
    if _planilha_configurada():
        try:
            aba = ABA_LANCAMENTOS
            try:
                aba = st.secrets["gsheets"].get("worksheet", ABA_LANCAMENTOS)
            except Exception:
                pass
            _conexao_planilha().update(worksheet=aba, data=df)
            st.cache_data.clear()
            return
        except Exception as e:
            st.warning(f"Não foi possível salvar na planilha ({e}). Salvando no arquivo local.")

    os.makedirs(os.path.dirname(ARQUIVO_LOCAL), exist_ok=True)
    df.to_csv(ARQUIVO_LOCAL, index=False)


# ---------------------------------------------------------------------------
# Autenticação simples (usuários definidos em .streamlit/secrets.toml)
# ---------------------------------------------------------------------------
def autenticar() -> str | None:
    usuarios = {}
    try:
        usuarios = dict(st.secrets.get("usuarios", {}))
    except Exception:
        usuarios = {}
    if not usuarios:
        usuarios = {"admin": {"senha": "admin", "nome": "Administrador", "role": "admin"}}

    if "usuario_logado" in st.session_state:
        return st.session_state["usuario_logado"]

    st.title("🔐 Login — Lançamento de Materiais")
    with st.form("login"):
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        ok = st.form_submit_button("Entrar")
    if ok:
        dados = usuarios.get(usuario)
        if dados and dados.get("senha") == senha:
            st.session_state["usuario_logado"] = usuario
            st.rerun()
        st.error("Usuário ou senha inválidos.")
    st.stop()


# ---------------------------------------------------------------------------
# Páginas
# ---------------------------------------------------------------------------
OPCAO_OUTRO = "✏️ Outro (informar manualmente)"


def pagina_lancar() -> None:
    st.header("📝 Novo lançamento de material")

    ativos = carregar_ativos()
    mapa_ativos = {}
    opcoes_login = []
    for _, r in ativos.iterrows():
        login = str(r["Login"]).strip()
        if not login:
            continue
        label = f"{login} — {r['Técnico']}" if str(r["Técnico"]).strip() else login
        opcoes_login.append(label)
        mapa_ativos[label] = r
    opcoes_por_re: dict[str, list[str]] = {}
    for label, ativo in mapa_ativos.items():
        re = _normalizar_re(ativo["RE"])
        if re:
            opcoes_por_re.setdefault(re, []).append(label)
    opcoes_login.append(OPCAO_OUTRO)

    def ao_escolher_login() -> None:
        sel = st.session_state.get("login_sel")
        if sel in mapa_ativos:
            ativo = mapa_ativos[sel]
            st.session_state["re_input"] = _normalizar_re(ativo["RE"])
            st.session_state["tecnico_input"] = str(ativo["Técnico"]).strip()
            st.session_state["login_manual"] = ""
        else:
            st.session_state["re_input"] = ""
            st.session_state["tecnico_input"] = ""
            st.session_state["login_manual"] = ""

    def ao_digitar_re() -> None:
        re = _normalizar_re(st.session_state.get("re_input", ""))
        correspondencias = opcoes_por_re.get(re, [])
        if correspondencias:
            sel_atual = st.session_state.get("login_sel")
            sel = sel_atual if sel_atual in correspondencias else correspondencias[0]
            st.session_state["login_sel"] = sel
            st.session_state["tecnico_input"] = str(
                mapa_ativos[sel]["Técnico"]
            ).strip()
            st.session_state["login_manual"] = ""
        else:
            st.session_state["login_sel"] = OPCAO_OUTRO
            st.session_state["tecnico_input"] = ""
            st.session_state["login_manual"] = ""

    if not ativos.empty:
        col_login, col_re = st.columns(2)
        col_login.selectbox(
            "Login p/ Inserir material (lista de ativos)",
            opcoes_login,
            key="login_sel",
            on_change=ao_escolher_login,
        )
        if "re_input" not in st.session_state:
            sel_inicial = st.session_state.get("login_sel")
            if sel_inicial in mapa_ativos:
                ativo = mapa_ativos[sel_inicial]
                st.session_state["re_input"] = _normalizar_re(ativo["RE"])
                st.session_state["tecnico_input"] = str(ativo["Técnico"]).strip()
    else:
        st.info("Lista de ativos vazia — informe o login manualmente.")
        col_re = st.container()

    col_re.text_input(
        "RE",
        key="re_input",
        placeholder="ex.: 8488",
        on_change=ao_digitar_re,
    )
    re_digitado = _normalizar_re(st.session_state.get("re_input", ""))
    if re_digitado and re_digitado not in opcoes_por_re:
        st.caption("RE não encontrado na lista de ativos; preencha os dados manualmente.")
    elif len(opcoes_por_re.get(re_digitado, [])) > 1:
        st.caption("Este RE está associado a mais de um login; confira a seleção.")

    with st.form("form_lancamento", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        data = col1.date_input("Data", value=date.today())
        contrato = col2.text_input("Contrato", placeholder="ex.: 423766173")
        wo = col3.text_input("WO", placeholder="ex.: FORA TOA GPON")

        col4, col5 = st.columns(2)
        sel = st.session_state.get("login_sel", OPCAO_OUTRO)
        if sel in mapa_ativos:
            login = mapa_ativos[sel]["Login"]
            col4.text_input("Login p/ Inserir material", value=login, disabled=True)
            tecnico = col5.text_input(
                "Técnico",
                value=str(st.session_state.get("tecnico_input", "")),
                placeholder="ex.: MAYKON DIAS GUIMARAES",
            )
        else:
            login = col4.text_input(
                "Login p/ Inserir material",
                placeholder="ex.: Z662724",
                key="login_manual",
            )
            tecnico = col5.text_input(
                "Técnico",
                value=str(st.session_state.get("tecnico_input", "")),
                placeholder="ex.: MAYKON DIAS GUIMARAES",
            )
        re = st.session_state.get("re_input", "").strip()

        col7, col8, col9 = st.columns(3)
        codigo_sap = col7.text_input("CÓDIGO SAP", placeholder="ex.: 22061736")
        descricao = col8.text_input("DESCRIÇÃO DO PRODUTO", placeholder="ex.: CABO DROP 1FO ...")
        um = col9.selectbox("UM.", UNIDADES)

        quantidade = st.number_input("QUANTIDADE", min_value=0, step=1, value=1)

        enviado = st.form_submit_button("💾 Salvar lançamento")

    if enviado:
        erros = []
        if not contrato.strip():
            erros.append("Contrato é obrigatório.")
        if not wo.strip():
            erros.append("WO é obrigatória.")
        if not codigo_sap.strip():
            erros.append("CÓDIGO SAP é obrigatório.")
        if not descricao.strip():
            erros.append("DESCRIÇÃO DO PRODUTO é obrigatória.")
        if quantidade <= 0:
            erros.append("QUANTIDADE deve ser maior que zero.")
        if erros:
            for e in erros:
                st.error(e)
            return

        novo = {
            "Data": data.strftime("%d/%m/%Y"),
            "Contrato": contrato.strip(),
            "WO": wo.strip(),
            "Login p/ Inserir material": login.strip(),
            "RE": re.strip(),
            "Técnico": tecnico.strip(),
            "CÓDIGO SAP": codigo_sap.strip(),
            "DESCRIÇÃO DO PRODUTO": descricao.strip(),
            "UM.": um,
            "QUANTIDADE": str(int(quantidade)),
        }
        df = carregar_dados()
        df = pd.concat([df, pd.DataFrame([novo])], ignore_index=True)
        salvar_dados(df)
        st.success("✅ Lançamento salvo com sucesso!")


def pagina_consultar() -> None:
    st.header("📋 Lançamentos registrados")
    df = carregar_dados()

    if df.empty:
        st.info("Nenhum lançamento registrado ainda.")
        return

    col_f1, col_f2, col_f3 = st.columns(3)
    contratos = sorted(df["Contrato"].unique())
    wos = sorted(df["WO"].unique())
    f_contrato = col_f1.multiselect("Filtrar por Contrato", contratos)
    f_wo = col_f2.multiselect("Filtrar por WO", wos)
    f_busca = col_f3.text_input("Buscar na descrição / código SAP")

    filtrado = df.copy()
    if f_contrato:
        filtrado = filtrado[filtrado["Contrato"].isin(f_contrato)]
    if f_wo:
        filtrado = filtrado[filtrado["WO"].isin(f_wo)]
    if f_busca:
        mask = (
            filtrado["DESCRIÇÃO DO PRODUTO"].str.contains(f_busca, case=False, na=False)
            | filtrado["CÓDIGO SAP"].str.contains(f_busca, case=False, na=False)
        )
        filtrado = filtrado[mask]

    st.metric("Total de itens", len(filtrado))
    st.dataframe(filtrado, use_container_width=True, hide_index=True)

    col_e1, col_e2 = st.columns(2)
    with col_e1:
        excel_buffer = BytesIO()
        filtrado.to_excel(excel_buffer, index=False, engine="openpyxl")
        st.download_button(
            "⬇️ Baixar Excel",
            data=excel_buffer.getvalue(),
            file_name="lancamentos_materiais.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with col_e2:
        st.download_button(
            "⬇️ Baixar CSV",
            data=filtrado.to_csv(index=False).encode("utf-8-sig"),
            file_name="lancamentos_materiais.csv",
            mime="text/csv",
        )

    with st.expander("🗑️ Excluir lançamentos"):
        opcoes = {
            f"{i} — {r['DESCRIÇÃO DO PRODUTO'][:40]} ({r['Contrato']} / {r['WO']})": i
            for i, r in filtrado.iterrows()
        }
        selecao = st.multiselect("Selecione os lançamentos para excluir", list(opcoes))
        if st.button("Excluir selecionados") and selecao:
            indices = [opcoes[s] for s in selecao]
            df = df.drop(index=indices).reset_index(drop=True)
            salvar_dados(df)
            st.success(f"{len(indices)} lançamento(s) excluído(s).")
            st.rerun()


# ---------------------------------------------------------------------------
# App principal
# ---------------------------------------------------------------------------
def main() -> None:
    usuario = autenticar()

    st.sidebar.title("📦 Lançamento de Materiais")
    st.sidebar.caption("Contratos Fora TOA")
    pagina = st.sidebar.radio("Navegação", ["Novo lançamento", "Consultar lançamentos"])
    st.sidebar.divider()
    st.sidebar.write(f"👤 {usuario}")
    if st.sidebar.button("Sair"):
        del st.session_state["usuario_logado"]
        st.rerun()

    if pagina == "Novo lançamento":
        pagina_lancar()
    else:
        pagina_consultar()


if __name__ == "__main__":
    main()
