import streamlit as st
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

# Configuração da página
st.set_page_config(
    page_title="Consulta de Motoristas - Shopee", 
    page_icon="🚗",
    layout="centered"
)

# Cabeçalho com logo e título
col1, col2 = st.columns([1, 8])
with col1:
    st.image("unnamed.png", width=150)
with col2:
    st.markdown("<h1 style='color:#f26c2d;'>Consulta de Motoristas - Shopee</h1>", unsafe_allow_html=True)

# Estilos CSS personalizados
st.markdown("""
    <style>
        body, .stApp {
            background-color: #2A2A2F;
            color: #f26c2d;
        }
        .stTextInput > div > div > input {
            background-color: #333;
            color: white;
            border: 1px solid #f26c2d;
        }
        .stDataFrame {
            background-color: #2c2c2c;
        }
        table {
            background-color: #2c2c2c;
        }
        .stButton>button {
            border: 1px solid #f26c2d;
            color: white;
        }
        .stButton>button:hover {
            border: 1px solid #f26c2d;
            background-color: #3a3a3a;
        }
    </style>
""", unsafe_allow_html=True)

# Conexão com o Google Sheets
file_name = "teste-motoristas-4f5250c96818.json"
Scopes = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

try:
    credencial = ServiceAccountCredentials.from_json_keyfile_name(
        filename=file_name,
        scopes=Scopes
    )
    gc = gspread.authorize(credencial)
    planilha = gc.open("PROGRAMAÇÃO FROTA - Belem - LPA-02")
    aba = planilha.worksheet("Programação")

    dados = aba.get_all_values()[2:]
    df = pd.DataFrame(dados[1:], columns=dados[0])

    colunas_para_filtro = ["NOME", "ID Driver", "Placa"]
    colunas_para_exibir = ["NOME", "Data Exp.", "Cidades", "Bairros", "Onda", "Gaiola"]
    colunas_necessarias = colunas_para_filtro + [col for col in colunas_para_exibir if col not in colunas_para_filtro]

    for col in colunas_necessarias:
        if col not in df.columns:
            st.error(f"Coluna ausente na planilha: {col}")
            st.stop()

    colunas_obrigatorias = ["NOME", "Cidades", "Bairros", "Onda", "Gaiola"]
    df_teste = df[colunas_obrigatorias].replace("", None)

    if df_teste.isnull().any().any():
        st.warning("🚧 A planilha ainda está sendo preenchida. Volte mais tarde.")
        st.stop()

    df_filtrado = df[colunas_necessarias]
    for col in colunas_necessarias:
        df_filtrado[col] = df_filtrado[col].fillna("").astype(str)

    if "nome_busca" not in st.session_state:
        st.session_state.nome_busca = ""
    if "id_busca" not in st.session_state:
        st.session_state.id_busca = ""
    if "placa_busca" not in st.session_state:
        st.session_state.placa_busca = ""
    if "liberar_consulta" not in st.session_state:
        st.session_state.liberar_consulta = False

    if st.button("🪑 Limpar filtros"):
        st.session_state.nome_busca = ""
        st.session_state.id_busca = ""
        st.session_state.placa_busca = ""
        st.session_state.liberar_consulta = False
        st.rerun()

    nome_busca = st.text_input("🔎 Buscar por NOME do motorista:", value=st.session_state.nome_busca).strip().upper()
    st.session_state.nome_busca = nome_busca

    id_busca = st.text_input("🆔 Buscar por ID do motorista:", value=st.session_state.id_busca).strip()
    st.session_state.id_busca = id_busca

    placa_busca = st.text_input("🚗 Buscar por PLACA:", value=st.session_state.placa_busca).strip().upper()
    st.session_state.placa_busca = placa_busca

    btn_label = "🔒 Bloquear Consulta" if st.session_state.liberar_consulta else "🔓 Liberar Consulta"
    if st.button(btn_label, use_container_width=True):
        st.session_state.liberar_consulta = not st.session_state.liberar_consulta
        st.rerun()

    if st.session_state.liberar_consulta:
        st.success("🔓 Consulta liberada - Os resultados estão visíveis")
    else:
        st.warning("🔒 Consulta bloqueada - Clique no botão acima para liberar")
        st.stop()

    resultados = df_filtrado.copy()
    if nome_busca:
        resultados = resultados[resultados["NOME"].str.upper().str.contains(nome_busca)]
    if id_busca:
        resultados = resultados[resultados["ID Driver"].str.contains(id_busca)]
    if placa_busca:
        resultados = resultados[resultados["Placa"].str.upper().str.contains(placa_busca)]

    if not resultados.empty:
        st.success(f"✅ {len(resultados)} motorista(s) encontrado(s)")

        colunas_para_verificar = ["Placa", "Cidades", "Bairros", "Onda", "Gaiola"]
        faltando_info = resultados[colunas_para_verificar].isin(["", None]).any(axis=1).any()
        if faltando_info:
            st.warning("⚠️ Algumas informações ainda estão sendo preenchidas")

        resultados = resultados.sort_values(by=["Onda", "NOME"], ascending=[True, True])
        resultados = resultados.drop(columns=["Placa", "ID Driver"])

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
                {'selector': 'th', 'props': [('background-color', '#000000'), ('color', 'white'), 
                                             ('font-weight', 'bold'), ('text-align', 'center')]},
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
                th, td {
                    padding: 12px !important;
                }
            </style>
        """, unsafe_allow_html=True)

        st.write(styled_df.to_html(escape=False), unsafe_allow_html=True)

    else:
        st.warning("❌ Nenhum motorista encontrado com os critérios informados")

except Exception as e:
    st.error(f"⛔ Erro ao acessar a planilha: {str(e)}")

# Rodapé
st.markdown("---")
st.caption("**Desenvolvido por Kayo Soares - LPA 03**")
