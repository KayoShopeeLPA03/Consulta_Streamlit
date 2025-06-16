import streamlit as st
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(
    page_title="Consulta de Motoristas - Shopee", 
    page_icon="🚗",
    layout="centered"
)

col1, col2 = st.columns([1, 8])
with col1:
    st.image("unnamed.png", width=150)
with col2:
    st.markdown("<h1 style='color:#f26c2d;'>Consulta de Motoristas - Shopee</h1>", unsafe_allow_html=True)

st.markdown("""
    <style>
        body, .stApp {
            background-color: #2A2A2F;
            color: #f26c2d;
        }
        .stTextInput > div > div > input {
            background-color: #333;
            color: white;
        }
        .stDataFrame {
            background-color: #2c2c2c;
        }
        table {
            background-color: #2c2c2c;
        }
    </style>
""", unsafe_allow_html=True)

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

    # Colunas necessárias
    colunas_para_filtro = ["NOME", "ID Driver", "Placa"]
    colunas_para_exibir = ["NOME", "Data Exp.", "Cidades", "Bairros", "Onda", "Gaiola"]
    colunas_necessarias = colunas_para_filtro + [col for col in colunas_para_exibir if col not in colunas_para_filtro]

    # Garantir que todas as colunas existem
    for col in colunas_necessarias:
        if col not in df.columns:
            st.error(f"Coluna ausente na planilha: {col}")
            st.stop()

    # 🔒 VERIFICAÇÃO: impede o app de abrir se houver campos obrigatórios vazios
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

    if st.button("🧹 Limpar filtros"):
        st.session_state.nome_busca = ""
        st.session_state.id_busca = ""
        st.session_state.placa_busca = ""
        st.rerun()

    nome_busca = st.text_input("🔎 Buscar por NOME do motorista:", value=st.session_state.nome_busca).strip().upper()
    st.session_state.nome_busca = nome_busca

    id_busca = st.text_input("🆔 Buscar por ID do motorista:", value=st.session_state.id_busca).strip()
    st.session_state.id_busca = id_busca

    placa_busca = st.text_input("🚗 Buscar por PLACA:", value=st.session_state.placa_busca).strip().upper()
    st.session_state.placa_busca = placa_busca

    resultados = df_filtrado

    if nome_busca:
        resultados = resultados[resultados["NOME"].str.upper().str.contains(nome_busca)]
    if id_busca:
        resultados = resultados[resultados["ID Driver"].str.contains(id_busca)]
    if placa_busca:
        resultados = resultados[resultados["Placa"].str.upper().str.contains(placa_busca)]

    if not resultados.empty:
        st.success(f"{len(resultados)} resultado(s) encontrado(s):")

        colunas_para_verificar = ["Placa", "Cidades", "Bairros", "Onda", "Gaiola"]
        faltando_info = resultados[colunas_para_verificar].isin(["", None]).any(axis=1).any()
        if faltando_info:
            st.warning("⚠️ Algumas informações ainda estão sendo preenchidas. A lista está em construção.")

        resultados = resultados.sort_values(by=["Onda", "NOME"], ascending=[True, True])

        # Oculta colunas da visualização
        colunas_ocultas = ["Placa", "ID Driver"]
        resultados = resultados.drop(columns=colunas_ocultas)

        def cor_onda(row):
            onda = row["Onda"].strip().lower()
            cor = ""
            if onda == "1º onda":
                cor = "background-color: #FF0101"
            elif onda == "2º onda":
                cor = "background-color: #E5C12E"
            elif onda == "3º onda":
                cor = "background-color: #378137"
            elif "última" in onda or "4º" in onda:
                cor = "background-color: #215ebc"
            return [cor if col == "Onda" else "" for col in resultados.columns]

        def estilizar_colunas(val):
            if val.strip() == "":
                return "background-color: #f8d7da"
            return "background-color: #444444; color: white"

        styled_df = (
            resultados.style
            .apply(cor_onda, axis=1)
            .applymap(estilizar_colunas, subset=["Gaiola", "Cidades", "Bairros"])
            .set_table_styles([
                {'selector': 'th', 'props': [('background-color', '#000000'), ('color', 'white'), ('font-weight', 'bold'), ('text-align', 'center')]},
                {'selector': 'td', 'props': [('text-align', 'center'), ('padding', '8px')]}
            ])
            .hide(axis="index")
        )

        st.markdown("""
            <style>
                table {
                    border-collapse: separate;
                    border-spacing: 0;
                    border: 1px solid #444;
                    border-radius: 10px;
                    overflow: hidden;
                    font-family: 'Segoe UI', sans-serif;
                    font-size: 14px;
                    color: white;
                }
                th, td {
                    padding: 10px;
                }
            </style>
        """, unsafe_allow_html=True)

        st.write(styled_df.to_html(escape=False), unsafe_allow_html=True)

    else:
        st.warning("Nenhum motorista encontrado com os critérios informados.")

except Exception as e:
    st.error(f"Erro ao acessar a planilha: {e}") 

st.markdown("---")
st.caption("**Desenvolvido por Kayo Soares - LPA 03**")
