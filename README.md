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

- Se houver uma planilha configurada em `.streamlit/secrets.toml` (seção `[gsheets]` com
  `spreadsheet` e `worksheet`), os dados são salvos no Google Sheets.
- Caso contrário, os dados ficam no arquivo local `dados/lancamentos.csv`.

## Login

Os usuários são definidos em `.streamlit/secrets.toml` na seção `[usuarios]`.
