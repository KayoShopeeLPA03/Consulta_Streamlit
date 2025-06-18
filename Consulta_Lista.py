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
        /* Seus estilos permanecem aqui */
    </style>
""", unsafe_allow_html=True)

# Conexão com o Google Sheets
try:
    credencial = ServiceAccountCredentials.from_json_keyfile_name(
        filename="teste-motoristas-4f5250c96818.json",
        scopes=[
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    gc = gspread.authorize(credencial)

    # Acessar planilha
    planilha = gc.open("PROGRAMAÇÃO FROTA - Belem - LPA-02")
    aba = planilha.worksheet("Programação")

    # Obter e processar dados
    dados = aba.get_all_values()[2:]
    df = pd.DataFrame(dados[1:], columns=dados[0])

    # Colunas necessárias
    colunas_necessarias = ["NOME", "ID Driver", "Placa", "Data Exp.", "Cidades", "Bairros", "Onda", "Gaiola"]
    
    # Verificar colunas
    for col in colunas_necessarias:
        if col not in df.columns:
            st.error(f"Coluna ausente: {col}")
            st.stop()

    # Verificar dados obrigatórios
    if df[["NOME", "Cidades", "Bairros", "Onda", "Gaiola"]].replace("", None).isnull().any().any():
        st.warning("🚧 Planilha incompleta. Volte mais tarde.")
        st.stop()

    # Gerenciamento de estado
    session_defaults = {
        "nome_busca": "",
        "id_busca": "",
        "placa_busca": "",
        "liberar_consulta": False
    }
    for key, value in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Limpar filtros
    if st.button("🧹 Limpar filtros"):
        for key in session_defaults:
            st.session_state[key] = session_defaults[key]
        st.rerun()

    # Campos de busca
    st.session_state.nome_busca = st.text_input(
        "🔎 Buscar por NOME:",
        value=st.session_state.nome_busca
    ).strip().upper()

    st.session_state.id_busca = st.text_input(
        "🆔 Buscar por ID:",
        value=st.session_state.id_busca
    ).strip()

    st.session_state.placa_busca = st.text_input(
        "🚗 Buscar por PLACA:",
        value=st.session_state.placa_busca
    ).strip().upper()

    # Botão toggle
    btn_label = "🔒 Bloquear" if st.session_state.liberar_consulta else "🔓 Liberar"
    if st.button(f"{btn_label} Consulta", type="primary"):
        st.session_state.liberar_consulta = not st.session_state.liberar_consulta
        st.rerun()

    if not st.session_state.liberar_consulta:
        st.warning("🔒 Consulta bloqueada")
        st.stop()
    
    st.success("🔓 Consulta liberada")

    # Aplicar filtros
    resultados = df.copy()
    if st.session_state.nome_busca:
        resultados = resultados[resultados["NOME"].str.upper().str.contains(st.session_state.nome_busca)]
    if st.session_state.id_busca:
        resultados = resultados[resultados["ID Driver"].str.contains(st.session_state.id_busca)]
    if st.session_state.placa_busca:
        resultados = resultados[resultados["Placa"].str.upper().str.contains(st.session_state.placa_busca)]

    # Exibir resultados
    if resultados.empty:
        st.warning("❌ Nenhum resultado encontrado")
        st.stop()

    st.success(f"✅ {len(resultados)} motorista(s) encontrado(s)")

    # Função de estilização corrigida
    def estilo_linha(row):
        estilo = []
        for col in resultados.columns:
            if col == "Onda":
                onda = row[col].lower()
                if "1º onda" in onda: estilo.append("background-color: #FF0101")
                elif "2º onda" in onda: estilo.append("background-color: #E5C12E")
                elif "3º onda" in onda: estilo.append("background-color: #378137")
                elif "última" in onda or "4º" in onda: estilo.append("background-color: #215ebc")
                else: estilo.append("")
            else:
                estilo.append("background-color: #444; color: white" if row[col] else "background-color: #f8d7da")
        return estilo

    # Exibir tabela estilizada
    st.dataframe(
        resultados.drop(columns=["ID Driver", "Placa"]).style.apply(
            estilo_linha, axis=1
        ).set_table_styles([
            {'selector': 'th', 'props': [('background', '#000'), ('color', 'white')]},
            {'selector': 'td', 'props': [('text-align', 'center')]}
        ]),
        height=500
    )

except Exception as e:
    st.error(f"⛔ Erro: {str(e)}")

# Rodapé
st.markdown("---")
st.caption("**Desenvolvido por Kayo Soares - LPA 03**")
