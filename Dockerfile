# Usa a imagem base do Python
FROM python:3.11-slim

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copia o arquivo requirements.txt para o diretório /app
COPY requirements.txt .

# Instala as dependências do sistema necessárias para face_recognition e dlib
RUN apt-get update && apt-get install -y 


# Copia o restante do código para o contêiner
COPY . .

# Instala as dependências do Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expõe a porta da aplicação
EXPOSE 8501

CMD ["streamlit", "run", "ConsultadeMotorista.py", "--server.port=8501", "--server.address=0.0.0.0"]
