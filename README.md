# lancamento-materiais

Sistema que lança os materiais dos contratos Fora TOA.

Aplicativo Streamlit para inserir e consultar os materiais lançados por contrato/WO,
com as colunas: **Data, Contrato, WO, Login p/ Inserir material, RE, Técnico, CÓDIGO SAP,
DESCRIÇÃO DO PRODUTO, UM. e QUANTIDADE**.

## Como executar

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Persistência dos dados

- Os lançamentos são salvos na aba **Lançamentos** da planilha Google Sheets configurada
  em `.streamlit/secrets.toml` (seção `[gsheets]`).
- Caso a planilha não esteja acessível, os dados ficam no arquivo local `dados/lancamentos.csv`.

## Lista de ativos (login)

- O campo **Login p/ Inserir material** é preenchido a partir da aba **Ativos** da planilha
  (colunas: Login, Técnico, RE). Ao escolher um login, **Técnico** e **RE** são preenchidos
  automaticamente.
- Também é possível escolher "Outro (informar manualmente)" para digitar um login fora da lista.

## Login

Os usuários são definidos em `.streamlit/secrets.toml` na seção `[usuarios]`.
