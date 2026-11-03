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
import materiais

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
CATEGORIAS_EVIDENCIA = ["Evidências"]

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
        "{ font-family: 'Manrope', 'Inter', Arial, sans-serif !important; } "
        # fundo suave com faixa gradiente no topo
        "[data-testid='stAppViewContainer'] { background: linear-gradient(180deg, #eef2ff 0%, #f8fafc 45%); } "
        "[data-testid='stAppViewContainer']::before { content: ''; display: block; height: 6px; "
        "background: linear-gradient(90deg, #4f46e5, #7c3aed, #0ea5e9); } "
        "[data-testid='stMainBlockContainer'] { max-width: 900px; padding-top: 1rem; } "
        "[data-testid='stHeader'] { background: transparent; } "
        # card central
        "[data-testid='stVerticalBlockBorderWrapper'] { background: #ffffff; border: 1px solid #e8eaf0; "
        "border-radius: 18px; padding: 1.75rem 2rem; box-shadow: 0 12px 32px rgba(15, 23, 42, 0.10); } "
        "[data-testid='stVerticalBlockBorderWrapper'] h2, [data-testid='stVerticalBlockBorderWrapper'] h3 "
        "{ color: #0f172a; border-bottom: 2px solid #eef0f4; padding-bottom: .45rem; margin-top: 1.4rem; "
        "letter-spacing: -0.01em; } "
        # campos
        "input, textarea, select { border-radius: 10px !important; border-color: #e2e8f0 !important; "
        "background: #fbfcfe !important; transition: border-color .15s, box-shadow .15s; } "
        "input:focus, textarea:focus, select:focus { border-color: #6366f1 !important; "
        "box-shadow: 0 0 0 3px rgba(99, 102, 241, .15) !important; background: #fff !important; } "
        # botões
        "[data-testid='stButton'] button { background: linear-gradient(135deg, #4f46e5, #6d28d9); color: #fff; "
        "border: none; border-radius: 12px; font-weight: 700; padding: .6rem 1.5rem; "
        "box-shadow: 0 4px 14px rgba(79, 70, 229, .35); transition: transform .12s, box-shadow .12s; } "
        "[data-testid='stButton'] button:hover { transform: translateY(-1px); "
        "box-shadow: 0 6px 18px rgba(79, 70, 229, .45); } "
        # barra lateral com marca
        "[data-testid='stSidebar'] { background: #ffffff; border-right: 1px solid #e8eaf0; } "
        "[data-testid='stSidebar'] [data-testid='stMarkdown'] h1 { font-size: 1.25rem; "
        "background: linear-gradient(90deg, #4f46e5, #0ea5e9); -webkit-background-clip: text; "
        "background-clip: text; color: transparent; } "
        # tabela e métricas
        "[data-testid='stDataFrame'] { border-radius: 12px; overflow: hidden; } "
        "[data-testid='stMetric'] { background: #f8fafc; border: 1px solid #e8eaf0; border-radius: 12px; padding: .5rem .75rem; } "
        "[data-testid='stMetricValue'] { color: #4f46e5; }"
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
    """Carrega o catálogo de materiais (de materiais.py) da planilha ou do CSV local."""
    if _planilha_configurada():
        return materiais.carregar_materiais(ler_planilha=_ler_planilha_fuzzy, avisar=st.warning)
    return materiais.carregar_materiais()


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
def pagina_lancar() -> None:
    st.title("Atendimento FORA TOA — SPO-TOTALLESTE")
    st.caption("Gestão de Material")

    # 3) Preenche o formulário ao duplicar um atendimento existente
    prefill = st.session_state.pop("prefill", None)
    if prefill:
        st.session_state["re_tec"] = prefill.get("RE", "")
        st.session_state["login_tec"] = prefill.get("Login p/ Inserir material", "")
        st.session_state["nome_tec"] = prefill.get("Técnico", "")
        st.session_state["contrato"] = prefill.get("Contrato", "")
        st.session_state["wo"] = prefill.get("WO", "")
        st.session_state["cep"] = prefill.get("CEP", "")
        st.session_state["endereco"] = prefill.get("Endereço", "")
        st.session_state["numero"] = prefill.get("Número", "")
        st.session_state["complemento"] = prefill.get("Complemento", "")
        st.toast("🔁 Atendimento duplicado — ajuste os materiais e registre!")

    ativos = carregar_ativos()
    mapa_por_re = {
        str(r["RE"]).strip(): r for _, r in ativos.iterrows() if str(r["RE"]).strip()
    }

    def ao_digitar_re() -> None:
        """Ao digitar o RE, puxa Login e Nome da lista de ativos."""
        re = str(st.session_state.get("re_tec", "")).strip()
        if re in mapa_por_re:
            r = mapa_por_re[re]
            st.session_state["login_tec"] = str(r["Login"]).strip()
            st.session_state["nome_tec"] = str(r["Técnico"]).strip()
        else:
            st.session_state.pop("login_tec", None)
            st.session_state.pop("nome_tec", None)

    def ao_digitar_cep() -> None:
        """Ao digitar o CEP, busca o endereço na API ViaCEP."""
        cep = str(st.session_state.get("cep", "")).strip()
        cep = "".join(ch for ch in cep if ch.isdigit())
        if len(cep) != 8:
            return
        try:
            import requests

            resp = requests.get(f"https://viacep.com.br/ws/{cep}/json/", timeout=5)
            dados = resp.json()
            if dados and not dados.get("erro"):
                logradouro = dados.get("logradouro", "")
                bairro = dados.get("bairro", "")
                end = f"{logradouro} - {bairro}".strip(" -")
                if end:
                    st.session_state["endereco"] = end
                if dados.get("complemento"):
                    st.session_state["complemento"] = dados["complemento"]
        except Exception:
            pass  # se a API falhar, o usuário preenche manualmente

    with st.container(border=True):
        st.subheader("Identificação do Técnico")
        col4, col5, col6 = st.columns(3)
        login = col4.text_input("Login", key="login_tec", placeholder="ex.: Z662724")
        re = col5.text_input("RE do Técnico *", key="re_tec", on_change=ao_digitar_re, placeholder="ex.: 8488")
        tecnico = col6.text_input("Nome *", key="nome_tec", placeholder="ex.: MAYKON DIAS GUIMARAES")
        if not ativos.empty and str(re).strip() in mapa_por_re:
            st.caption(f"✅ Técnico encontrado na lista de ativos: {mapa_por_re[str(re).strip()]['Técnico']}")

        st.subheader("Dados do Contrato")
        col1, col2, col3 = st.columns(3)
        contrato = col1.text_input("Contrato *", placeholder="ex.: 423766173")
        tipo = col2.selectbox("Tipo de Atendimento", TIPOS_ATENDIMENTO, key="tipo")
        data = col3.date_input("Data do Contrato *", value=date.today())
        wo = st.text_input("WO", placeholder="ex.: FORA TOA GPON")

        st.subheader("Endereço")
        col_e1, col_e2 = st.columns(2)
        cep = col_e1.text_input("CEP *", key="cep", on_change=ao_digitar_cep, placeholder="ex.: 09000-000")
        endereco = col_e2.text_input("Endereço *", key="endereco", placeholder="Rua, avenida...")
        col_e3, col_e4 = st.columns(2)
        numero = col_e3.text_input("Número", key="numero")
        complemento = col_e4.text_input("Complemento", key="complemento")
        if str(cep).strip():
            st.caption("💡 Digite o CEP para buscar o endereço automaticamente (ViaCEP).")

        st.subheader("Materiais Utilizados")
        materiais = carregar_materiais()
        itens = []  # (codigo, descricao, quantidade)
        if not materiais.empty:
            mapa_mat = {
                f"{r['CÓDIGO SAP']} — {r['DESCRIÇÃO DO PRODUTO']}": r for _, r in materiais.iterrows()
            }
            selecao = st.multiselect(
                "Materiais", list(mapa_mat), help="Busque pelo código SAP ou descrição"
            )
            if selecao:
                cols_qtd = st.columns(min(len(selecao), 4))
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

        st.subheader("Evidências")
        fotos_por_categoria = {}
        for cat in CATEGORIAS_EVIDENCIA:
            with st.expander(cat):
                up = st.file_uploader(
                    f"Adicionar fotos — {cat}",
                    type=["png", "jpg", "jpeg"],
                    accept_multiple_files=True,
                    key=f"ev_{cat}",
                )
                fotos_por_categoria[cat] = up or []

        st.subheader("Observações")
        observacoes = st.text_area("Observações", placeholder="Registre aqui observações do atendimento...")

        enviado = st.button("Registrar Atendimento", type="primary", use_container_width=True)

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
        if not cep.strip():
            erros.append("CEP é obrigatório.")
        elif len("".join(ch for ch in cep if ch.isdigit())) != 8:
            erros.append("CEP deve ter 8 dígitos.")
        if not endereco.strip():
            erros.append("Endereço é obrigatório.")
        if re.strip() and not re.strip().isdigit():
            erros.append("RE deve conter apenas números.")
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

        for categoria, fotos in fotos_por_categoria.items():
            if not fotos:
                continue
            pasta = os.path.join("dados", "evidencias", contrato.strip(), categoria)
            os.makedirs(pasta, exist_ok=True)
            for foto in fotos:
                with open(os.path.join(pasta, foto.name), "wb") as f:
                    f.write(foto.getbuffer())

        st.success(f"✅ Atendimento registrado com sucesso! ({len(linhas)} material(is))")
        st.balloons()
        st.rerun()


def pagina_consultar() -> None:
    st.header("📋 Lançamentos registrados")
    df = carregar_dados()

    if df.empty:
        st.info("Nenhum lançamento registrado ainda.")
        return

    col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(5)
    contratos = sorted(df["Contrato"].unique())
    wos = sorted(df["WO"].unique())
    res = sorted(df["RE"].unique())
    tecnicos = sorted(df["Técnico"].unique())
    f_contrato = col_f1.multiselect("Contrato", contratos)
    f_wo = col_f2.multiselect("WO", wos)
    f_re = col_f3.multiselect("RE", res)
    f_tec = col_f4.multiselect("Técnico", tecnicos)
    f_busca = col_f5.text_input("Buscar (código, descrição, contrato)")

    filtrado = df.copy()
    if f_contrato:
        filtrado = filtrado[filtrado["Contrato"].isin(f_contrato)]
    if f_wo:
        filtrado = filtrado[filtrado["WO"].isin(f_wo)]
    if f_re:
        filtrado = filtrado[filtrado["RE"].isin(f_re)]
    if f_tec:
        filtrado = filtrado[filtrado["Técnico"].isin(f_tec)]
    if f_busca:
        mask = (
            filtrado["DESCRIÇÃO DO PRODUTO"].str.contains(f_busca, case=False, na=False)
            | filtrado["CÓDIGO SAP"].str.contains(f_busca, case=False, na=False)
            | filtrado["Contrato"].str.contains(f_busca, case=False, na=False)
            | filtrado["Técnico"].str.contains(f_busca, case=False, na=False)
        )
        filtrado = filtrado[mask]

    # 5) Filtrar somente os lançamentos do próprio RE
    meus = st.checkbox("👤 Apenas meus lançamentos")
    if meus:
        meu_re = st.text_input("Seu RE", key="meu_re")
        if meu_re.strip():
            filtrado = filtrado[filtrado["RE"] == meu_re.strip()]

    qtd_total = pd.to_numeric(filtrado["QUANTIDADE"], errors="coerce").sum()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Registros", len(filtrado))
    m2.metric("Quantidade total", int(qtd_total))
    m3.metric("Contratos", filtrado["Contrato"].nunique())
    m4.metric("Técnicos", filtrado["Técnico"].nunique())

    # 2) Edição inline dos lançamentos
    editado = st.data_editor(
        filtrado, use_container_width=True, hide_index=True, num_rows="fixed",
        key="editor_lancamentos",
    )
    if st.button("💾 Salvar alterações"):
        df.loc[filtrado.index, COLUNAS] = editado[COLUNAS].astype(str).values
        salvar_dados(df)
        st.success("Alterações salvas com sucesso!")
        st.rerun()

    # 3) Duplicar atendimento (reaproveita contrato/endereço/técnico)
    with st.expander("🔁 Duplicar atendimento"):
        opcoes_dup = {
            f"{r['Contrato']} — {r['Técnico']} ({r['Data']})": i for i, r in df.iterrows()
        }
        escolha = st.selectbox("Escolha um atendimento para duplicar", list(opcoes_dup))
        if st.button("Duplicar") and escolha:
            r = df.loc[opcoes_dup[escolha]]
            st.session_state["prefill"] = {c: str(r.get(c, "")) for c in COLUNAS}
            st.session_state["nav"] = "Registrar Atendimento"
            st.rerun()

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


def pagina_dashboard() -> None:
    """Dashboard: gráficos e relatório diário dos atendimentos."""
    st.header("📊 Dashboard")
    df = carregar_dados()

    if df.empty:
        st.info("Nenhum lançamento registrado ainda.")
        return

    df["QUANTIDADE_N"] = pd.to_numeric(df["QUANTIDADE"], errors="coerce").fillna(0)

    st.subheader("Materiais mais utilizados")
    top = (
        df.groupby("DESCRIÇÃO DO PRODUTO", as_index=False)["QUANTIDADE_N"]
        .sum()
        .sort_values("QUANTIDADE_N", ascending=False)
        .head(10)
    )
    if not top.empty:
        import plotly.express as px

        fig = px.bar(
            top, x="QUANTIDADE_N", y="DESCRIÇÃO DO PRODUTO", orientation="h",
            color="QUANTIDADE_N", color_continuous_scale="Indigo",
            labels={"QUANTIDADE_N": "Quantidade", "DESCRIÇÃO DO PRODUTO": "Material"},
        )
        fig.update_layout(yaxis=dict(autorange="reversed"), height=420, margin=dict(t=20))
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Quantidade por contrato")
    por_contrato = (
        df.groupby("Contrato", as_index=False)["QUANTIDADE_N"].sum().sort_values("QUANTIDADE_N", ascending=False)
    )
    if not por_contrato.empty:
        import plotly.express as px

        fig2 = px.bar(
            por_contrato, x="Contrato", y="QUANTIDADE_N",
            labels={"QUANTIDADE_N": "Quantidade", "Contrato": "Contrato"},
            color="QUANTIDADE_N", color_continuous_scale="Blues",
        )
        fig2.update_layout(height=320, margin=dict(t=20))
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("📅 Relatório diário")
    hoje = date.today().strftime("%d/%m/%Y")
    do_hoje = df[df["Data"] == hoje]
    c1, c2 = st.columns(2)
    c1.metric("Atendimentos hoje", do_hoje["Contrato"].nunique())
    c2.metric("Materiais lançados hoje", int(do_hoje["QUANTIDADE_N"].sum()))
    if not do_hoje.empty:
        st.dataframe(do_hoje.drop(columns=["QUANTIDADE_N"]), use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️ Baixar relatório de hoje (CSV)",
            data=do_hoje.drop(columns=["QUANTIDADE_N"]).to_csv(index=False).encode("utf-8-sig"),
            file_name=f"relatorio_{date.today().isoformat()}.csv",
            mime="text/csv",
        )
    else:
        st.caption(f"Nenhum atendimento registrado em {hoje}.")


# ---------------------------------------------------------------------------
# App principal
# ---------------------------------------------------------------------------
def main() -> None:
    injetar_estilos()

    st.sidebar.title("📦 Lançamento de Materiais")
    st.sidebar.caption("Contratos Fora TOA · SPO-TOTALLESTE")
    pagina = st.sidebar.radio(
        "Navegação",
        ["Registrar Atendimento", "Consultar lançamentos", "Dashboard"],
        key="nav",
    )

    if pagina == "Registrar Atendimento":
        pagina_lancar()
    elif pagina == "Consultar lançamentos":
        pagina_consultar()
    else:
        pagina_dashboard()


if __name__ == "__main__":
    main()
