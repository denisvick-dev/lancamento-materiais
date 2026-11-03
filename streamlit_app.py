# -*- coding: utf-8 -*-
"""
Lançamento de Materiais — Contratos Fora TOA
Sistema para inserir e consultar os materiais lançados por contrato/WO.
"""
import base64
import os
from io import BytesIO
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
    "Tipo de Atendimento",
    "WO",
    "Login p/ Inserir material",
    "RE",
    "Técnico",
    "CÓDIGO SAP",
    "DESCRIÇÃO DO PRODUTO",
    "UM.",
    "QUANTIDADE",
    "Observações",
]

TIPOS_ATENDIMENTO = ["Encaixe FORA TOA", "Encaixe TOA"]

ARQUIVO_CATALOGO = "catalogo_materiais.csv"
ABA_MATERIAIS = "Materiais"

UNIDADES = ["UN.", "M", "M²", "M³", "CX", "PC", "KG", "L", "RL"]

PASTA_FONTES = "fonts"


FONTES_CORPORATIVAS = {
    "Inter": [400, 500, 700],
    "Manrope": [400, 500, 600, 700, 800],
    "Roboto": [400, 500, 700],
}


def injetar_estilos() -> None:
    """Injeta as fontes corporativas (Inter/Manrope/Roboto) embutidas do repositório."""
    faces = ""
    for familia, pesos in FONTES_CORPORATIVAS.items():
        for peso in pesos:
            caminho = os.path.join(PASTA_FONTES, f"{familia.lower()}-{peso}.woff2")
            if os.path.exists(caminho):
                with open(caminho, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                faces += (
                    f"@font-face {{ font-family: '{familia}'; font-style: normal; "
                    f"font-weight: {peso}; font-display: swap; "
                    f"src: url(data:font/woff2;base64,{b64}) format('woff2'); }}\n"
                )
    css = faces + (
        "html, body, [class*='css'], .stMarkdown, .stButton, input, textarea, select "
        "{ font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif !important; } "
        "h1, h2, h3, h4, h5, h6, .stTitle "
        "{ font-family: 'Manrope', 'Inter', Arial, sans-serif !important; }"
    )
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


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


@st.cache_resource(show_spinner=False)
def _cliente_gspread():
    """Cliente gspread autenticado com a conta de serviço dos secrets."""
    import gspread

    sa = dict(st.secrets["gcp_service_account"])
    return gspread.service_account_from_dict(sa)


def _ler_planilha(worksheet, ttl: str = "5m") -> pd.DataFrame | None:
    """Lê uma aba da planilha Google via gspread; retorna None se vazia/falhar."""
    ss = _cliente_gspread().open_by_key(_spreadsheet_id())
    ws = ss.worksheet(worksheet) if isinstance(worksheet, str) else ss.get_worksheet(worksheet)
    valores = ws.get_all_values()
    if not valores:
        return None
    df = pd.DataFrame(valores[1:], columns=valores[0])
    if df.empty:
        return None
    return df


def _ler_planilha_fuzzy(nome_aba: str) -> pd.DataFrame | None:
    """Lê a aba pelo nome exato; se não existir, tenta nome parecido ou a 1ª aba."""
    ss = _cliente_gspread().open_by_key(_spreadsheet_id())
    nomes = [w.title for w in ss.worksheets()]
    alvo = None
    if nome_aba in nomes:
        alvo = nome_aba
    else:
        alvo = next(
            (n for n in nomes if nome_aba.lower() in n.lower() or n.lower() in nome_aba.lower()),
            nomes[0] if nomes else None,
        )
    if alvo is None:
        return None
    return _ler_planilha(alvo)


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


@st.cache_data(ttl=300, show_spinner=False)
def carregar_ativos() -> pd.DataFrame:
    """Carrega a lista de ativos (login, técnico e RE) da planilha Google."""
    colunas = ["Login", "Técnico", "RE"]
    if _planilha_configurada():
        try:
            aba = ABA_ATIVOS
            try:
                aba = st.secrets["gsheets"].get("ativos_worksheet", ABA_ATIVOS)
            except Exception:
                pass
            df = _ler_planilha_fuzzy(aba)
            if df is not None:
                return _normalizar_colunas(df, colunas)
        except Exception as e:
            st.warning(f"Não foi possível ler a lista de ativos na planilha ({e}). Usando arquivo local.")

    if os.path.exists(ARQUIVO_ATIVOS):
        df = pd.read_csv(ARQUIVO_ATIVOS, dtype=str)
        return _normalizar_colunas(df, colunas)
    return pd.DataFrame(columns=colunas)


@st.cache_data(ttl=300, show_spinner=False)
def carregar_materiais() -> pd.DataFrame:
    """Carrega o catálogo de materiais (CÓDIGO SAP + descrição) da planilha ou do CSV local."""
    colunas = ["CÓDIGO SAP", "DESCRIÇÃO DO PRODUTO"]
    if _planilha_configurada():
        try:
            df = _ler_planilha(ABA_MATERIAIS)
            if df is not None:
                return _normalizar_colunas(df, colunas)
        except Exception as e:
            st.warning(f"Não foi possível ler o catálogo de materiais ({e}). Usando CSV local.")

    if os.path.exists(ARQUIVO_CATALOGO):
        df = pd.read_csv(ARQUIVO_CATALOGO, dtype=str)
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
            client = _cliente_gspread()
            ss = client.open_by_key(_spreadsheet_id())
            try:
                ws = ss.worksheet(aba)
            except Exception:
                ws = ss.add_worksheet(title=aba, rows=1000, cols=len(COLUNAS))
            ws.clear()
            ws.update([COLUNAS] + df.values.tolist())
            st.cache_data.clear()
            return
        except Exception as e:
            st.warning(f"Não foi possível salvar na planilha ({e}). Salvando no arquivo local.")

    os.makedirs(os.path.dirname(ARQUIVO_LOCAL), exist_ok=True)
    df.to_csv(ARQUIVO_LOCAL, index=False)


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
    opcoes_login.append(OPCAO_OUTRO)

    def ao_escolher_login() -> None:
        sel = st.session_state.get("login_sel")
        if sel in mapa_ativos:
            st.session_state["tec_auto"] = mapa_ativos[sel]["Técnico"]
            st.session_state["re_auto"] = mapa_ativos[sel]["RE"]
        else:
            st.session_state.pop("tec_auto", None)
            st.session_state.pop("re_auto", None)

    if not ativos.empty:
        st.selectbox(
            "Login (lista de ativos)",
            opcoes_login,
            key="login_sel",
            on_change=ao_escolher_login,
        )
    else:
        st.info("Lista de ativos vazia — informe o login manualmente.")

    with st.form("form_lancamento", clear_on_submit=True):
        st.subheader("👤 Identificação do Técnico")
        col4, col5, col6 = st.columns(3)
        sel = st.session_state.get("login_sel", OPCAO_OUTRO)
        if sel in mapa_ativos:
            login = mapa_ativos[sel]["Login"]
            col4.text_input("Login", value=login, disabled=True)
            re = col5.text_input("RE do Técnico *", value=str(st.session_state.get("re_auto", "")), placeholder="ex.: 8488")
            tecnico = col6.text_input("Nome *", value=str(st.session_state.get("tec_auto", "")), placeholder="ex.: MAYKON DIAS GUIMARAES")
        else:
            login = col4.text_input("Login *", placeholder="ex.: Z662724")
            re = col5.text_input("RE do Técnico *", placeholder="ex.: 8488")
            tecnico = col6.text_input("Nome *", placeholder="ex.: MAYKON DIAS GUIMARAES")

        st.subheader("📄 Dados do Contrato")
        col1, col2, col3 = st.columns(3)
        contrato = col1.text_input("Contrato *", placeholder="ex.: 423766173")
        tipo = col2.selectbox("Tipo de Atendimento", TIPOS_ATENDIMENTO)
        data = col3.date_input("Data do Contrato *", value=date.today())
        wo = st.text_input("WO", placeholder="ex.: FORA TOA GPON")

        st.subheader("📦 Materiais Utilizados")
        materiais = carregar_materiais()
        itens = []  # (codigo, descricao, quantidade)
        if not materiais.empty:
            mapa_mat = {
                f"{r['CÓDIGO SAP']} — {r['DESCRIÇÃO DO PRODUTO']}": r for _, r in materiais.iterrows()
            }
            selecao = st.multiselect(
                "Selecione os materiais", list(mapa_mat), help="Busque pelo código SAP ou descrição"
            )
            cols_qtd = st.columns(min(len(selecao), 4) or 1)
            for i, s in enumerate(selecao):
                qtd = cols_qtd[i % len(cols_qtd)].number_input(
                    f"Qtd. {s.split(' — ')[0]}", min_value=0, step=1, value=1, key=f"qtd_{i}"
                )
                itens.append((mapa_mat[s]["CÓDIGO SAP"], mapa_mat[s]["DESCRIÇÃO DO PRODUTO"], qtd))
        else:
            col7, col8, col9 = st.columns(3)
            codigo_sap = col7.text_input("CÓDIGO SAP *", placeholder="ex.: 22061736")
            descricao = col8.text_input("DESCRIÇÃO DO PRODUTO *", placeholder="ex.: CABO DROP 1FO ...")
            quantidade = col9.number_input("QUANTIDADE *", min_value=0, step=1, value=1)
            itens.append((codigo_sap, descricao, quantidade))

        st.subheader("🖼️ Evidências (fotos)")
        fotos = st.file_uploader("Adicionar fotos", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

        st.subheader("📝 Observações")
        observacoes = st.text_area("Observações", placeholder="Registre aqui observações do atendimento...")

        enviado = st.form_submit_button("💾 Registrar Atendimento")

    if enviado:
        erros = []
        if not contrato.strip():
            erros.append("Contrato é obrigatório.")
        if not login.strip():
            erros.append("Login é obrigatório.")
        if not re.strip():
            erros.append("RE do Técnico é obrigatória.")
        if not tecnico.strip():
            erros.append("Nome do técnico é obrigatório.")
        if not itens or all(not c.strip() or not d.strip() for c, d, _ in itens):
            erros.append("Selecione ao menos um material.")
        if any(q <= 0 for _, _, q in itens if q is not None):
            erros.append("A quantidade de cada material deve ser maior que zero.")
        if erros:
            for e in erros:
                st.error(e)
            return

        linhas = []
        for codigo_sap, descricao, quantidade in itens:
            if not codigo_sap.strip() or not descricao.strip():
                continue
            linhas.append({
                "Data": data.strftime("%d/%m/%Y"),
                "Contrato": contrato.strip(),
                "Tipo de Atendimento": tipo,
                "WO": wo.strip(),
                "Login p/ Inserir material": login.strip(),
                "RE": re.strip(),
                "Técnico": tecnico.strip(),
                "CÓDIGO SAP": codigo_sap.strip(),
                "DESCRIÇÃO DO PRODUTO": descricao.strip(),
                "UM.": "UN.",
                "QUANTIDADE": str(int(quantidade)),
                "Observações": observacoes.strip(),
            })
        df = carregar_dados()
        df = pd.concat([df, pd.DataFrame(linhas)], ignore_index=True)
        salvar_dados(df)

        if fotos:
            pasta = os.path.join("dados", "evidencias", contrato.strip())
            os.makedirs(pasta, exist_ok=True)
            for foto in fotos:
                with open(os.path.join(pasta, foto.name), "wb") as f:
                    f.write(foto.getbuffer())

        st.success(f"✅ Atendimento registrado com sucesso! ({len(linhas)} material(is))")


def pagina_consultar() -> None:
    st.header("📋 Lançamentos registrados")
    df = carregar_dados()

    if df.empty:
        st.info("Nenhum lançamento registrado ainda.")
        return

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    contratos = sorted(df["Contrato"].unique())
    wos = sorted(df["WO"].unique())
    res = sorted(df["RE"].unique())
    f_contrato = col_f1.multiselect("Filtrar por Contrato", contratos)
    f_wo = col_f2.multiselect("Filtrar por WO", wos)
    f_re = col_f3.multiselect("Filtrar por RE", res)
    f_busca = col_f4.text_input("Buscar na descrição / código SAP")

    filtrado = df.copy()
    if f_contrato:
        filtrado = filtrado[filtrado["Contrato"].isin(f_contrato)]
    if f_wo:
        filtrado = filtrado[filtrado["WO"].isin(f_wo)]
    if f_re:
        filtrado = filtrado[filtrado["RE"].isin(f_re)]
    if f_busca:
        mask = (
            filtrado["DESCRIÇÃO DO PRODUTO"].str.contains(f_busca, case=False, na=False)
            | filtrado["CÓDIGO SAP"].str.contains(f_busca, case=False, na=False)
        )
        filtrado = filtrado[mask]

    st.metric("Total de itens", len(filtrado))
    st.dataframe(filtrado, use_container_width=True, hide_index=True)

    excel_buffer = BytesIO()
    filtrado.to_excel(excel_buffer, index=False, engine="openpyxl")
    excel_buffer.seek(0)

    col_e1, col_e2 = st.columns(2)
    with col_e1:
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
    injetar_estilos()

    st.sidebar.title("📦 Lançamento de Materiais")
    st.sidebar.caption("Contratos Fora TOA")
    pagina = st.sidebar.radio("Navegação", ["Novo lançamento", "Consultar lançamentos"])

    if pagina == "Novo lançamento":
        pagina_lancar()
    else:
        pagina_consultar()


if __name__ == "__main__":
    main()
