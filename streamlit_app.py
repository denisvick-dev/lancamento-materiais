import streamlit as st

# Define o título da página do aplicativo
st.title("Hello World!")

# Adiciona um texto simples abaixo do título
st.write("Bem-vindo ao seu primeiro aplicativo com o Streamlit!")

# Cria um campo interativo de texto
nome = st.text_input("Qual é o seu nome?")

# Exibe uma mensagem personalizada se o usuário digitar algo
if nome:
    st.write(f"Olá, {nome}! É um prazer ter você aqui.")