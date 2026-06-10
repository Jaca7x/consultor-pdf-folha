import streamlit as st
import pdfplumber
import re
import csv
import io

st.set_page_config(page_title="Extrator de Folha", page_icon="📄")
st.title("📄 Extrator de Folha de Pagamento")
st.write("Envie o PDF e baixe o CSV com os dados principais.")

def extrair_dados(arquivo):
    with pdfplumber.open(arquivo) as pdf:
        paginas = [p.extract_text() or "" for p in pdf.pages]
    texto = "\n".join(paginas)

    m = re.search(r'Empresa:\s*[\d.,]', texto)
    codigo_empresa = m.group(1).strip() if m else "NÃO ENCONTRADO"
    nome_empresa = m.group(2).strip() if m else "NÃO ENCONTRADO"

    m = re.search(r'1 - Empregado\s+(\d+)', texto)
    qtd = m.group(1) if m else "NÃO ENCONTRADO"

    m = re.search(
        r'Totais\s*\n\s*Proventos:\s*[\d.,]+\s+Vantagens:\s*[\d.,]+\s+Descontos:\s*[\d.,]+\s+L[íi]quido:\s*([\d.,]+)',
        texto
    )
    liquido = m.group(1) if m else "NÃO ENCONTRADO"

    m = re.search(r'Total CP SEGURADOS\s+([\d.,]+)', texto)
    inss = m.group(1) if m else "NÃO ENCONTRADO"

    m = re.search(r'Total IRRF\s+([\d.,]+)\s+0,00', texto)
    irrf = m.group(1) if m else "NÃO ENCONTRADO"

    m = re.search(r'Total FGTS Mensal\s+\d+\s+([\d.,]+)', texto)
    fgts = m.group(1) if m else "NÃO ENCONTRADO"

    return {
        "Codigo_Empresa": codigo_empresa,
        "Nome_Empresa": nome_empresa,
        "Qtd_Funcionarios": qtd,
        "Total_Liquido": liquido,
        "INSS_Segurados": inss,
        "IRRF_Total": irrf,
        "FGTS_Mensal": fgts,
    }

arquivo = st.file_uploader("Escolha o PDF", type="pdf")

if arquivo:
    with st.spinner("Extraindo dados..."):
        dados = extrair_dados(arquivo)

    st.success("Dados extraídos!")
    st.table(dados.items())

    saida = io.StringIO()
    writer = csv.DictWriter(saida, fieldnames=dados.keys(), delimiter=";")
    writer.writeheader()
    writer.writerow(dados)

    st.download_button(
        label="⬇️ Baixar CSV",
        data=saida.getvalue().encode("utf-8-sig"),
        file_name="folha.csv",
        mime="text/csv"
    )