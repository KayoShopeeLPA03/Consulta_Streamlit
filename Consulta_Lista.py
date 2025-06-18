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

# Estilos
st.markdown("""
    <style>
        body, .stApp { background-color: #2A2A2F; color: #f26c2d; }
        .stTextInput > div > div > input {
            background-color: #333; color: white; border: 1px solid #f26c2d;
        }
        .stButton>button {
            border: 1px solid #f26c2d; color: white;
        }
        .stButton>button:hover {
            background-color: #3a3a3a;
        }
    </style>
""", unsafe_allow_html=True)

# Cabeçalho
col1, col2 = st.columns([1, 8])
with col1:
    st.image("unnamed.png", width=150)
with col2:
    st.markdown("<h1 style='color:#f26c2d;'>Consulta de Motoristas - Shopee</h1>", unsafe_allow_html=True)

# Caminhos
file_name = "teste-motoristas-4f5250c96818.json"
backup_path = "dados_cache.csv"
Scopes = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# Atualizar manual
if st.button("🔄 Atualizar dados"):
    st.cache_data.clear()
    st.rerun()

@st.cache_data(ttl=60)
def carregar_dados():
    credencial = ServiceAccountCredentials.from_json_keyfile_name(file_name, scopes=Scopes)
    gc = gspread.authorize(credencial)
    planilha = gc.open("PROGRAMAÇÃO FROTA - Belem - LPA-02")
    aba = planilha.worksheet("Programação")
    dados = aba.get_all_values()[2:]
    df = pd.DataFrame(dados[1:], columns=dados[0])
    df.to_csv(backup_path, index=False)  # backup local
    return df

# Tenta carregar dados
try:
    df = carregar_dados()
except Exception as e:
    st.warning("⚠️ Falha na API do Google Sheets. Dados carregados do backup local.")
    if os.path.exists(backup_path):
        df = pd.read_csv(backup_path)
    else:
        st.error("⛔ Sem conexão e sem backup local disponível.")
        st.stop()

# Colunas
colunas_para_filtro = ["NOME", "ID Driver", "Placa"]
colunas_para_exibir = ["NOME", "Data Exp.", "Cidades", "Bairros", "Onda", "Gaiola"]
colunas_necessarias = colunas_para_filtro + [c for c in colunas_para_exibir if c not in colunas_para_filtro]

# Verifica estrutura
for col in colunas_necessarias:
    if col not in df.columns:
        st.error(f"Coluna ausente: {col}")
        st.stop()

# Checagem de preenchimento
df_teste = df[["NOME", "Cidades", "Bairros", "Onda", "Gaiola"]].replace("", None)
if df_teste.isnull().any().any():
    st.warning("🚧 A planilha ainda está sendo preenchida. Volte mais tarde.")
    st.stop()

# Preparar dados
df_filtrado = df[colunas_necessarias].fillna("").astype(str)

# Filtros
if "nome_busca" not in st.session_state:
    st.session_state.nome_busca = ""
if "id_busca" not in st.session_state:
    st.session_state.id_busca = ""
if "placa_busca" not in st.session_state:
    st.session_state.placa_busca = ""
if "liberar_consulta" not in st.session_state:
    st.session_state.liberar_consulta = False

# Botão limpar
if st.button("🧹 Limpar filtros"):
    st.session_state.nome_busca = ""
    st.session_state.id_busca = ""
    st.session_state.placa_busca = ""
    st.session_state.liberar_consulta = False
    st.rerun()

# Inputs
nome_busca = st.text_input("🔎 Buscar por NOME:", value=st.session_state.nome_busca).strip().upper()
st.session_state.nome_busca = nome_busca

id_busca = st.text_input("🆔 Buscar por ID:", value=st.session_state.id_busca).strip()
st.session_state.id_busca = id_busca

placa_busca = st.text_input("🚗 Buscar por PLACA:", value=st.session_state.placa_busca).strip().upper()
st.session_state.placa_busca = placa_busca

# Toggle
btn_label = "🔒 Bloquear Consulta" if st.session_state.liberar_consulta else "🔓 Liberar Consulta"
if st.button(btn_label, use_container_width=True):
    st.session_state.liberar_consulta = not st.session_state.liberar_consulta
    st.rerun()

# Liberação
if st.session_state.liberar_consulta:
    st.success("🔓 Consulta liberada")
else:
    st.warning("🔒 Consulta bloqueada")
    st.stop()

# Filtro em dados
resultados = df_filtrado.copy()
if nome_busca:
    resultados = resultados[resultados["NOME"].str.upper().str.contains(nome_busca)]
if id_busca:
    resultados = resultados[resultados["ID Driver"].str.contains(id_busca)]
if placa_busca:
    resultados = resultados[resultados["Placa"].str.upper().str.contains(placa_busca)]

# Resultado
if not resultados.empty:
    st.success(f"✅ {len(resultados)} resultado(s) encontrado(s).")

    col_verif = ["Placa", "Cidades", "Bairros", "Onda", "Gaiola"]
    if resultados[col_verif].isin(["", None]).any().any():
        st.warning("⚠️ Algumas informações ainda estão sendo preenchidas.")

    resultados = resultados.sort_values(by=["Onda", "NOME"]).drop(columns=["Placa", "ID Driver"])

    def estilo_onda(val):
        onda = val.strip().lower()
        if onda == "1º onda": return "background-color: #B22222; color: white"
        elif onda == "2º onda": return "background-color: #E5C12E; color: white"
        elif onda == "3º onda": return "background-color: #378137; color: white"
        elif "última" in onda or "4º" in onda: return "background-color: #215ebc; color: white"
        return "background-color: #444444; color: white"

    styled_df = resultados.style \
        .applymap(estilo_onda, subset=["Onda"]) \
        .applymap(lambda x: 'background-color: #f8d7da' if x.strip() == "" else "background-color: #444444; color: white", 
                  subset=["Gaiola", "Cidades", "Bairros"]) \
        .set_table_styles([
            {'selector': 'th', 'props': [('background-color', '#000000'), ('color', 'white'), ('font-weight', 'bold'), ('text-align', 'center')]},
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
else:
    st.warning("❌ Nenhum motorista encontrado com os critérios informados.")

# Rodapé
st.markdown("---")
st.caption("**Desenvolvido por Kayo Soares - LPA 03**")
