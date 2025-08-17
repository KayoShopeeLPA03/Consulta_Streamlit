import streamlit as st
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import os
from typing import List, Dict, Set

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

# Estilos adaptáveis
st.markdown(f"""
    <style>
        body, .stApp {{ background-color: #2A2A2F; color: {texto_cor}; }}
        .stTextInput > div > div > input {{
            background-color: {fundo_input}; color: {texto_cor}; border: 1px solid {cor_borda};
        }}
        .stButton>button {{
            border: 1px solid {cor_borda}; color: {texto_cor};
        }}
        .stButton>button:hover {{
            background-color: #3a3a3a;
        }}
    </style>
""", unsafe_allow_html=True)

# Cabeçalho
col1, col2 = st.columns([1, 8])
with col1:
    st.image("unnamed.png", width=150)
with col2:
    st.markdown(f"<h1 style='color:{cor_borda};'>Consulta de Motoristas - Shopee</h1>", unsafe_allow_html=True)

# ==============================
# Parâmetros e cache
# ==============================
file_name = "teste-motoristas-4f5250c96818.json"
backup_path = "dados_cache.csv"
Scopes = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# ------------------------------
# Utilidades de normalização
# ------------------------------
# Mapeia possíveis nomes/variações de cabeçalho para um nome padrão
COL_ALIASES: Dict[str, Set[str]] = {
    "NOME": {"NOME", "Nome", "nome"},
    "ID Driver": {"ID Driver", "IDDriver", "ID", "ID DRIVER", "Id Driver", "id driver"},
    "Placa": {"Placa", "PLACA", "placa"},
    "Data Exp.": {"Data Exp.", "Data Exp", "DATA EXP.", "DATA EXP", "DataExp", "data exp.", "data exp"},
    "Cidades": {"Cidades", "Cidade", "cidades", "cidade"},
    "Bairros": {"Bairros", "Bairro", "bairros", "bairro"},
    "Onda": {"Onda", "onda", "ONDA"},
    "Gaiola": {"Gaiola", "GAIOLA", "gaiola"},
}

# Conjunto mínimo para detectar o cabeçalho (pode ampliar se quiser)
REQUIRED_HEADER_MIN: Set[str] = {"NOME", "ID Driver", "Placa"}

def _normalize_header_names(cols: List[str]) -> List[str]:
    """Renomeia colunas conforme o dicionário de aliases."""
    out = []
    for c in cols:
        c_clean = str(c).strip()
        mapped = None
        for target, aliases in COL_ALIASES.items():
            if c_clean in aliases:
                mapped = target
                break
        out.append(mapped if mapped else c_clean)
    return out

def _find_header_index(rows: List[List[str]], search_rows: int = 20) -> int:
    """
    Encontra a linha do cabeçalho nas primeiras `search_rows` linhas
    procurando as colunas mínimas obrigatórias (após normalização).
    """
    for i, row in enumerate(rows[:search_rows]):
        norm = set(_normalize_header_names([str(c).strip() for c in row]))
        if REQUIRED_HEADER_MIN.issubset(norm):
            return i
    return -1

def _normalize_gaiola(series: pd.Series) -> pd.Series:
    """Padroniza valores de Gaiola, convertendo 'NS-1' == 'NS1' e limpando espaços."""
    return (
        series.astype(str)
              .str.strip()
              .str.replace(r"\s*-\s*", "", regex=True)
    )

# ------------------------------
# Botão de atualização manual
# ------------------------------
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

# Campos de busca
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

# ==============================
# Carregamento de dados (dinâmico + backup)
# ==============================
@st.cache_data(ttl=300)  # cache por 5 minutos
def carregar_dados() -> pd.DataFrame:
    cred = ServiceAccountCredentials.from_json_keyfile_name(file_name, scopes=Scopes)
    gc = gspread.authorize(cred)
    planilha = gc.open("PROGRAMAÇÃO FROTA - Belem - LPA-02")
    aba = planilha.worksheet("Programação")

    raw = aba.get_all_values()  # todas as linhas
    if not raw or len(raw) == 0:
        raise ValueError("Planilha vazia.")

    # Encontrar a linha do cabeçalho
    header_idx = _find_header_index(raw, search_rows=20)
    if header_idx < 0:
        raise ValueError("Não encontrei o cabeçalho com as colunas obrigatórias (NOME, ID Driver, Placa).")

    # Cabeçalho normalizado
    header_original = [str(c).strip() for c in raw[header_idx]]
    header = _normalize_header_names(header_original)

    # Corpo de dados (linhas após o cabeçalho)
    data = raw[header_idx + 1:]
    # Remove linhas totalmente vazias
    data = [r for r in data if any(str(c).strip() for c in r)]

    # Ajusta o comprimento das linhas ao tamanho do cabeçalho
    width = len(header)
    data = [r[:width] + [""] * (width - len(r)) if len(r) < width else r[:width] for r in data]

    df = pd.DataFrame(data, columns=header)

    # Normalizações
    df.columns = [c.strip() for c in df.columns]
    for c in df.columns:
        df[c] = df[c].astype(str).str.strip()

    # Tratar Gaiola
    if "Gaiola" in df.columns:
        df["Gaiola"] = _normalize_gaiola(df["Gaiola"])

    # Salva backup local
    df.to_csv(backup_path, index=False, encoding="utf-8")
    return df

# Carregando dados
try:
    df = carregar_dados()
except Exception as e:
    st.warning(f"⚠️ Falha na API do Google Sheets ({e}). Carregando do backup local.")
    if os.path.exists(backup_path):
        df = pd.read_csv(backup_path, dtype=str).fillna("")
    else:
        st.error("⛔ Sem conexão e sem backup disponível.")
        st.stop()

# ==============================
# Validação e filtros
# ==============================
col_filtro = ["NOME", "ID Driver", "Placa"]
col_exibir = ["NOME", "Data Exp.", "Cidades", "Bairros", "Onda", "Gaiola"]
col_necessarias = col_filtro + [c for c in col_exibir if c not in col_filtro]

# Checa colunas necessárias
for col in col_necessarias:
    if col not in df.columns:
        st.error(f"Coluna ausente: {col}")
        st.stop()

# Remove linhas com NOME vazio e normaliza strings
df = df[col_necessarias].fillna("").astype(str)
df = df[df["NOME"].str.strip() != ""]

# Verifica preenchimento essencial
essential_cols = ["NOME", "Cidades", "Bairros", "Onda", "Gaiola"]
if df[essential_cols].applymap(lambda x: str(x).strip() == "").any().any():
    st.warning("🚧 Planilha ainda sendo preenchida.")
    # Você pode optar por não dar stop aqui, mas manteremos como no original
    st.stop()

# Aplicar filtros
resultados = df.copy()
if st.session_state.nome_busca:
    resultados = resultados[resultados["NOME"].str.upper().str.contains(st.session_state.nome_busca, na=False)]
if st.session_state.id_busca:
    resultados = resultados[resultados["ID Driver"].str.contains(st.session_state.id_busca, na=False)]
if st.session_state.placa_busca:
    resultados = resultados[resultados["Placa"].str.upper().str.contains(st.session_state.placa_busca, na=False)]

# ==============================
# Exibir resultados
# ==============================
if resultados.empty:
    st.warning("❌ Nenhum motorista encontrado.")
else:
    st.success(f"✅ {len(resultados)} motorista(s) encontrado(s).")

    # Aviso se houver campos em branco nos principais
    if resultados[["Placa", "Cidades", "Bairros", "Onda", "Gaiola"]].applymap(lambda x: str(x).strip() == "").any().any():
        st.warning("⚠️ Algumas informações ainda estão sendo preenchidas.")

    # Ordenação e colunas exibidas
    resultados = resultados.sort_values(by=["Onda", "NOME"]).drop(columns=["Placa", "ID Driver"])

    def estilo_onda(val: str):
        onda = str(val).strip().lower()
        if onda == "1º onda" or onda == "1ª onda" or onda == "1a onda":
            return "background-color: #B22222; color: white"
        elif onda == "2º onda" or onda == "2ª onda" or onda == "2a onda":
            return "background-color: #E5C12E; color: white"
        elif onda == "3º onda" or onda == "3ª onda" or onda == "3a onda":
            return "background-color: #378137; color: white"
        elif "última" in onda or "4º" in onda or "4ª" in onda or "4a" in onda:
            return "background-color: #215ebc; color: white"
        return f"background-color: #444444; color: {texto_cor}"

    styled_df = (
        resultados.style
        .applymap(estilo_onda, subset=["Onda"])
        .applymap(lambda x: 'background-color: #f8d7da' if str(x).strip() == "" else f"background-color: #444444; color: {texto_cor}",
                  subset=["Gaiola", "Cidades", "Bairros"])
        .set_table_styles([
            {'selector': 'th', 'props': [('background-color', '#000000'), ('color', texto_cor), ('font-weight', 'bold'), ('text-align', 'center')]},
            {'selector': 'td', 'props': [('text-align', 'center'), ('padding', '8px')]},
            {'selector': '', 'props': [('border', '1px solid #444')]}
        ])
        .hide(axis="index")
    )

    st.markdown("""
        <style>
            .dataframe {
                border-radius: 10px;
                overflow: hidden;
                font-family: 'Segoe UI', sans-serif;
            }
            th, td { padding: 12px !important; }
        </style>
    """, unsafe_allow_html=True)

    # Render do HTML do Styler
    st.write(styled_df.to_html(escape=False), unsafe_allow_html=True)

# Rodapé
st.markdown("---")
st.caption("**Desenvolvido por Kayo Soares - LPA 03**")
