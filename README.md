# lancamento-materiais

Sistema que lança os materiais dos contratos Fora TOA.

Aplicativo Streamlit para registrar atendimentos e lançar os materiais por contrato/WO,
seguindo a estrutura do Atendimento FORA TOA — SPO-TOTALLESTE (Gestão de Material):

- **Identificação do Técnico** (Login da lista de ativos, RE e Nome preenchidos automaticamente)
- **Dados do Contrato** (Contrato, Tipo de Atendimento, Data, WO)
- **Materiais Utilizados** (seleção no catálogo `catalogo_materiais.csv` / aba "Materiais" da planilha, com quantidade por item)
- **Evidências** (upload de fotos, salvas em `dados/evidencias/<contrato>/`)
- **Observações**

Colunas salvas: **Data, Contrato, Tipo de Atendimento, WO, Login p/ Inserir material, RE,
Técnico, CÓDIGO SAP, DESCRIÇÃO DO PRODUTO, UM., QUANTIDADE, Observações**.

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

## Consulta por RE

A tela de consulta possui filtro por **RE**, além de Contrato, WO e busca livre
por código SAP / descrição. Use **Extrair lançamentos (Excel)** ou
**Extrair lançamentos (CSV)** para baixar os resultados filtrados.

## Fontes corporativas

As fontes **Inter** (texto), **Manrope** (títulos) e **Roboto** estão na pasta
`fonts/` (arquivos woff2 + licenças) e são aplicadas via CSS embutido no app.
