import streamlit as st
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import os
from datetime import datetime

# ==============================
# Configuração da página
# ==============================
st.set_page_config(
    page_title="Consulta de Motoristas - Shopee",
    page_icon="🚗",
    layout="centered"
)

# Detectar tema escuro ou claro
if st.get_option("theme.base") == "Light":
    texto_cor = "#000000"
    fundo_input = "#ffffff"
    cor_borda = "#f26c2d"
else:
    texto_cor = "#ffffff"
    fundo_input = "#333333"
    cor_borda = "#f26c2d"

# Estilos adaptáveis (inputs + SELECTBOX estilizado)
st.markdown(f"""
    <style>
        body, .stApp {{ background-color: #2A2A2F; color: {texto_cor}; }}

        /* Text Input */
        .stTextInput > div > div > input {{
            background-color: {fundo_input};
            color: {texto_cor};
            border: 1px solid {cor_borda};
            border-radius: 12px;
            padding: 8px 12px;
            transition: box-shadow .2s ease, transform .05s ease;
        }}
        .stTextInput > div > div > input:focus {{
            outline: none !important;
            box-shadow: 0 0 0 3px rgba(242,108,45,.45);
        }}

        /* Buttons */
        .stButton>button {{
            border: 1px solid {cor_borda};
            color: {texto_cor};
            border-radius: 12px;
            padding: 8px 12px;
        }}
        .stButton>button:hover {{ background-color: #3a3a3a; }}

        /* SELECTBOX (aplica a todos os selects) */
        div[data-testid="stSelectbox"] > div {{
            background-color: {fundo_input};
            border: 1px solid {cor_borda};
            border-radius: 12px;
            padding: 2px 10px;
            transition: box-shadow .2s ease, transform .05s ease;
        }}
        div[data-testid="stSelectbox"] > div:hover {{
            box-shadow: 0 0 0 2px rgba(242,108,45,.25);
        }}
        div[data-testid="stSelectbox"] > div:focus-within {{
            box-shadow: 0 0 0 3px rgba(242,108,45,.45);
        }}
        div[data-testid="stSelectbox"] label {{
            color: {texto_cor};
            font-weight: 600;
        }}

        /* Tabelas */
        .dataframe {{
            border-radius: 10px;
            overflow: hidden;
            font-family: 'Segoe UI', sans-serif;
        }}
        th, td {{ padding: 12px !important; }}
    </style>
""", unsafe_allow_html=True)

# Cabeçalho
col1, col2 = st.columns([1, 8])
with col1:
    st.image("unnamed.png", width=150)
with col2:
    st.markdown(f"<h1 style='color:{cor_borda};'>Consulta de Motoristas - Shopee</h1>", unsafe_allow_html=True)

# Carimbo de build para confirmar atualização
st.caption(f"Build: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ==============================
# Parâmetros e cache
# ==============================
file_name = "teste-motoristas-4f5250c96818.json"
backup_path = "dados_cache.csv"
Scopes = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# Botão de atualização manual
if st.button("🔄 Atualizar dados"):
    st.cache_data.clear()
    st.rerun()

# Session state inicial
for key in ["nome_busca", "id_busca", "placa_busca", "liberar_consulta"]:
    if key not in st.session_state:
        st.session_state[key] = "" if key != "liberar_consulta" else False

# Botão limpar
if st.button("🧹 Limpar filtros"):
    for k in ["nome_busca", "id_busca", "placa_busca"]:
        st.session_state[k] = ""
    st.session_state.liberar_consulta = False
    st.rerun()

# Campos de busca (texto livre)
st.session_state.nome_busca = st.text_input("🔎 Buscar por NOME:", value=st.session_state.nome_busca).strip().upper()
st.session_state.id_busca = st.text_input("🆔 Buscar por ID:", value=st.session_state.id_busca).strip()
st.session_state.placa_busca = st.text_input("🚗 Buscar por PLACA:", value=st.session_state.placa_busca).strip().upper()

# Botão de liberação
btn_label = "🔒 Bloquear Consulta" if st.session_state.liberar_consulta else "🔓 Liberar Consulta"
if st.button(btn_label, use_container_width=True):
    st.session_state.liberar_consulta = not st.session_state.liberar_consulta
    st.rerun()

# Só carrega dados se estiver liberado
if not st.session_state.liberar_consulta:
    st.warning("🔒 Consulta bloqueada. Clique no botão acima para liberar.")
    st.stop()

# ---------- Helpers ----------
def _find_header_index(rows, required_upper={"NOME", "ID DRIVER", "PLACA"}, search_rows=30):
    """Encontra dinamicamente a linha do cabeçalho nas primeiras linhas."""
    for i, row in enumerate(rows[:search_rows]):
        row_upper = {str(c).strip().upper() for c in row}
        if required_upper.issubset(row_upper):
            return i
    raise ValueError(
        "Não encontrei o cabeçalho com as colunas obrigatórias: " + ", ".join(sorted(required_upper))
    )

def estilo_onda(val: str):
    o = str(val).strip().lower()
    if o in {"1º onda", "1ª onda", "1a onda"}:
        return "background-color: #B22222; color: white"
    if o in {"2º onda", "2ª onda", "2a onda"}:
        return "background-color: #E5C12E; color: white"
    if o in {"3º onda", "3ª onda", "3a onda"}:
        return "background-color: #378137; color: white"
    if "última" in o or "4º" in o or "4ª" in o or "4a" in o:
        return "background-color: #215ebc; color: white"
    return f"background-color: #444444; color: {texto_cor}"

def render_tabela(df_show: pd.DataFrame):
    styled = (
        df_show.style
        .applymap(estilo_onda, subset=["Onda"] if "Onda" in df_show.columns else [])
        .applymap(
            lambda x: 'background-color: #f8d7da' if str(x).strip() == "" else f"background-color: #444444; color: {texto_cor}",
            subset=[c for c in ["Gaiola", "Cidades", "Bairros"] if c in df_show.columns]
        )
        .set_table_styles([
            {'selector': 'th', 'props': [('background-color', '#000000'), ('color', texto_cor), ('font-weight', 'bold'), ('text-align', 'center')]},
            {'selector': 'td', 'props': [('text-align', 'center'), ('padding', '8px')]},
            {'selector': '', 'props': [('border', '1px solid #444')]}
        ])
        .hide(axis="index")
    )
    st.write(styled.to_html(escape=False), unsafe_allow_html=True)

# ---------- Carga dinâmica ----------
@st.cache_data(ttl=300)  # cache por 5 minutos
def carregar_dados():
    cred = ServiceAccountCredentials.from_json_keyfile_name(file_name, scopes=Scopes)
    gc = gspread.authorize(cred)
    planilha = gc.open("PROGRAMAÇÃO FROTA - Belem - LPA-02")
    aba = planilha.worksheet("Programação")

    raw = aba.get_all_values()
    if not raw:
        raise ValueError("Planilha vazia.")

    header_idx = _find_header_index(raw, required_upper={"NOME", "ID DRIVER", "PLACA"}, search_rows=30)
    header = [str(c).strip() for c in raw[header_idx]]
    data = raw[header_idx + 1:]
    data = [r for r in data if any(str(c).strip() for c in r)]

    width = len(header)
    data = [r[:width] + [""] * (width - len(r)) if len(r) < width else r[:width] for r in data]

    df = pd.DataFrame(data, columns=header)

    # Normalização de nomes de colunas
    CANON = {
        "NOME": "NOME",
        "ID DRIVER": "ID Driver",
        "PLACA": "Placa",
        "DATA EXP.": "Data Exp.",
        "CIDADES": "Cidades",
        "BAIRROS": "Bairros",
        "ONDA": "Onda",
        "GAIOLA": "Gaiola",
    }
    df.columns = [CANON.get(c.strip().upper(), c.strip()) for c in df.columns]

    # Ajuste de Gaiola (NS-1 == NS1)
    if "Gaiola" in df.columns:
        df["Gaiola"] = (
            df["Gaiola"].astype(str)
                         .str.strip()
                         .str.replace(r"\s*-\s*", "", regex=True)
        )

    df.to_csv(backup_path, index=False, encoding="utf-8")
    return df

# Carregando dados
try:
    df = carregar_dados()
except Exception as e:
    st.warning(f"⚠️ Falha na API do Google Sheets ({e}). Dados carregados do backup local.")
    if os.path.exists(backup_path):
        df = pd.read_csv(backup_path, dtype=str).fillna("")
    else:
        st.error("⛔ Sem conexão e sem backup disponível.")
        st.stop()

# ==============================
# Validação e base
# ==============================
col_filtro = ["NOME", "ID Driver", "Placa"]
col_exibir = ["NOME", "Data Exp.", "Cidades", "Bairros", "Onda", "Gaiola"]
col_necessarias = col_filtro + [c for c in col_exibir if c not in col_filtro]
for col in col_necessarias:
    if col not in df.columns:
        st.error(f"Coluna ausente: {col}")
        st.stop()

df = df[col_necessarias].fillna("").astype(str)

# Somente avisa se houver preenchimento pendente (NÃO dá stop)
if df[["NOME", "Cidades", "Bairros", "Onda", "Gaiola"]].applymap(lambda x: str(x).strip() == "").any().any():
    st.warning("🚧 Planilha ainda sendo preenchida. Alguns campos podem estar vazios.")

# -------------------- Abas --------------------
tab1, tab2 = st.tabs(["🔎 Consulta", "🧭 Rotas disponíveis"])

# ==== Aba 1: Consulta ====
with tab1:
    base = df[df["NOME"].str.strip() != ""].copy()

    # Opções para selects (derivadas da base)
    ondas_opts    = ["Todas"] + sorted([o for o in base["Onda"].dropna().unique() if str(o).strip()])
    cidades_opts  = ["Todas"] + sorted([c for c in base["Cidades"].dropna().unique() if str(c).strip()])

    colf1, colf2, colf3 = st.columns(3)
    with colf1:
        filtro_onda_tab1 = st.selectbox("🛰️ Onda", options=ondas_opts, index=0, key="sel_onda_tab1")
    with colf2:
        filtro_cidade_tab1 = st.selectbox("🏙️ Cidade", options=cidades_opts, index=0, key="sel_cidade_tab1")

    # Bairros dependem da Cidade selecionada
    if filtro_cidade_tab1 == "Todas":
        bairros_base_tab1 = base["Bairros"]
    else:
        bairros_base_tab1 = base.loc[base["Cidades"] == filtro_cidade_tab1, "Bairros"]

    bairros_opts_tab1 = ["Todos"] + sorted([b for b in bairros_base_tab1.dropna().unique() if str(b).strip()])
    with colf3:
        filtro_bairro_tab1 = st.selectbox("📍 Bairro", options=bairros_opts_tab1, index=0, key="sel_bairro_tab1")

    # Aplica filtros + textos livres
    resultados = base.copy()
    if filtro_onda_tab1 != "Todas":
        resultados = resultados[resultados["Onda"] == filtro_onda_tab1]
    if filtro_cidade_tab1 != "Todas":
        resultados = resultados[resultados["Cidades"] == filtro_cidade_tab1]
    if filtro_bairro_tab1 != "Todos":
        resultados = resultados[resultados["Bairros"] == filtro_bairro_tab1]

    if st.session_state.nome_busca:
        resultados = resultados[resultados["NOME"].str.upper().str.contains(st.session_state.nome_busca, na=False)]
    if st.session_state.id_busca:
        resultados = resultados[resultados["ID Driver"].str.contains(st.session_state.id_busca, na=False)]
    if st.session_state.placa_busca:
        resultados = resultados[resultados["Placa"].str.upper().str.contains(st.session_state.placa_busca, na=False)]

    if resultados.empty:
        st.warning("❌ Nenhum motorista encontrado.")
    else:
        st.success(f"✅ {len(resultados)} motorista(s) encontrado(s).")
        tabela = resultados.sort_values(by=["Onda", "NOME"]).drop(columns=["Placa", "ID Driver"])
        render_tabela(tabela)

# ==== Aba 2: Rotas disponíveis ====
with tab2:
    # Rota disponível: NOME composto só por hífens (ex.: "-" ou "--")
    rotas = df[df["NOME"].astype(str).str.strip().str.fullmatch(r"-+").fillna(False)].copy()

    # Normalização
    for c in ["Onda", "Cidades", "Bairros"]:
        if c in rotas.columns:
            rotas[c] = rotas[c].astype(str).str.strip()

    # Opções das listas
    ondas_opts2    = ["Todas"] + sorted([o for o in rotas["Onda"].dropna().unique() if o])
    cidades_opts2  = ["Todas"] + sorted([c for c in rotas["Cidades"].dropna().unique() if c])

    colf1, colf2, colf3 = st.columns(3)
    with colf1:
        filtro_onda = st.selectbox("🛰️ Onda", options=ondas_opts2, index=0, key="sel_onda_tab2")
    with colf2:
        filtro_cidade = st.selectbox("🏙️ Cidade", options=cidades_opts2, index=0, key="sel_cidade_tab2")

    # Bairros dependem da cidade escolhida
    if filtro_cidade == "Todas":
        bairros_base = rotas["Bairros"]
    else:
        bairros_base = rotas.loc[rotas["Cidades"] == filtro_cidade, "Bairros"]

    bairros_opts = ["Todos"] + sorted([b for b in bairros_base.dropna().unique() if str(b).strip()])
    with colf3:
        filtro_bairro = st.selectbox("📍 Bairro", options=bairros_opts, index=0, key="sel_bairro_tab2")

    # Aplica filtros
    if filtro_onda != "Todas":
        rotas = rotas[rotas["Onda"] == filtro_onda]
    if filtro_cidade != "Todas":
        rotas = rotas[rotas["Cidades"] == filtro_cidade]
    if filtro_bairro != "Todos":
        rotas = rotas[rotas["Bairros"] == filtro_bairro]

    if rotas.empty:
        st.info("Nenhuma rota livre encontrada com os filtros atuais.")
    else:
        st.success(f"🧭 {len(rotas)} rota(s) livre(s) encontrada(s).")
        cols_rotas = [c for c in ["Data Exp.", "Cidades", "Bairros", "Onda", "Gaiola", "Placa"] if c in rotas.columns]
        tabela_rotas = rotas[cols_rotas].sort_values(
            by=[c for c in ["Onda", "Cidades", "Bairros"] if c in cols_rotas]
        )
        render_tabela(tabela_rotas)

# Rodapé
st.markdown("---")
st.caption("**Desenvolvido por Kayo Soares - LPA 03**")


