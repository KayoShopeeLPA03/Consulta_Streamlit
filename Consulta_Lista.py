import streamlit as st
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import os

# Configuração da página
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

# Parâmetros e cache
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

# Função cacheada de carregamento
@st.cache_data(ttl=300)  # cache por 5 minutos
def carregar_dados():
    cred = ServiceAccountCredentials.from_json_keyfile_name(file_name, scopes=Scopes)
    gc = gspread.authorize(cred)
    planilha = gc.open("PROGRAMAÇÃO FROTA - Belem - LPA-02")
    aba = planilha.worksheet("Programação")
    dados = aba.get_all_values()[3:]
    df = pd.DataFrame(dados[1:], columns=dados[0])
    df.to_csv(backup_path, index=False)
    return df

# Carregando dados
try:
    df = carregar_dados()
except Exception:
    st.warning("⚠️ Falha na API do Google Sheets. Dados carregados do backup local.")
    if os.path.exists(backup_path):
        df = pd.read_csv(backup_path)
    else:
        st.error("⛔ Sem conexão e sem backup disponível.")
        st.stop()

# Valida colunas
col_filtro = ["NOME", "ID Driver", "Placa"]
col_exibir = ["NOME", "Data Exp.", "Cidades", "Bairros", "Onda", "Gaiola"]
col_necessarias = col_filtro + [c for c in col_exibir if c not in col_filtro]

for col in col_necessarias:
    if col not in df.columns:
        st.error(f"Coluna ausente: {col}")
        st.stop()

# Verifica preenchimento essencial
if df[["NOME", "Cidades", "Bairros", "Onda", "Gaiola"]].replace("", None).isnull().any().any():
    st.warning("🚧 Planilha ainda sendo preenchida.")
    st.stop()

# Preparar e filtrar
df = df[col_necessarias].fillna("").astype(str)
df = df[df["NOME"] != ""]
resultados = df.copy()

if st.session_state.nome_busca:
    resultados = resultados[resultados["NOME"].str.upper().str.contains(st.session_state.nome_busca)]
if st.session_state.id_busca:
    resultados = resultados[resultados["ID Driver"].str.contains(st.session_state.id_busca)]
if st.session_state.placa_busca:
    resultados = resultados[resultados["Placa"].str.upper().str.contains(st.session_state.placa_busca)]

# Exibir resultados
if resultados.empty:
    st.warning("❌ Nenhum motorista encontrado.")
else:
    st.success(f"✅ {len(resultados)} motorista(s) encontrado(s).")

    if resultados[["Placa", "Cidades", "Bairros", "Onda", "Gaiola"]].isin(["", None]).any().any():
        st.warning("⚠️ Algumas informações ainda estão sendo preenchidas.")

    resultados = resultados.sort_values(by=["Onda", "NOME"]).drop(columns=["Placa", "ID Driver"])

    def estilo_onda(val):
        onda = val.strip().lower()
        if onda == "1º onda": return "background-color: #B22222; color: white"
        elif onda == "2º onda": return "background-color: #E5C12E; color: white"
        elif onda == "3º onda": return "background-color: #378137; color: white"
        elif "última" in onda or "4º" in onda: return "background-color: #215ebc; color: white"
        return f"background-color: #444444; color: {texto_cor}"

    styled_df = resultados.style \
        .applymap(estilo_onda, subset=["Onda"]) \
        .applymap(lambda x: 'background-color: #f8d7da' if x.strip() == "" else f"background-color: #444444; color: {texto_cor}",
                  subset=["Gaiola", "Cidades", "Bairros"]) \
        .set_table_styles([
            {'selector': 'th', 'props': [('background-color', '#000000'), ('color', texto_cor), ('font-weight', 'bold'), ('text-align', 'center')]},
            {'selector': 'td', 'props': [('text-align', 'center'), ('padding', '8px')]},
            {'selector': '', 'props': [('border', '1px solid #444')]}
        ]) \
        .hide(axis="index")

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

    st.write(styled_df.to_html(escape=False), unsafe_allow_html=True)

# Rodapé
st.markdown("---")
st.caption("**Desenvolvido por Kayo Soares - LPA 03**")

