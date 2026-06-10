import streamlit as st
import pdfplumber
import re
import csv
import io
import json
import os

st.set_page_config(page_title="Extrator de Folha", page_icon="📄")
st.title("📄 Extrator de Folha de Pagamento")

STORAGE_FILE = "dados_folhas.json"

def carregar_dados():
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def salvar_dados(dados):
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def extrair_dados(arquivo):
    with pdfplumber.open(arquivo) as pdf:
        paginas = [p.extract_text() or "" for p in pdf.pages]
    texto = "\n".join(paginas)

    m = re.search(r'Empresa:\s*(\d+) - (.+?)\s+\d{2}/\d{2}/\d{4}', texto)
    codigo_empresa = m.group(1).strip() if m else "NÃO ENCONTRADO"
    nome_empresa   = m.group(2).strip() if m else "NÃO ENCONTRADO"

    m = re.search(r'1 - Empregado\s+(\d+)', texto)
    qtd = m.group(1) if m else "NÃO ENCONTRADO"

    m = re.search(
        r'Totais\s*\n\s*Proventos:\s*[\d.,]+\s+Vantagens:\s*[\d.,]+\s+Descontos:\s*[\d.,]+\s+L[íi]quido:\s*([\d.,]+)',
        texto
    )
    liquido = m.group(1) if m else "NÃO ENCONTRADO"

    m = re.search(r'11 - FGTS mensal\s+([\d.,]+)', texto)
    fgts_11 = m.group(1) if m else "NÃO ENCONTRADO"

    m = re.search(r'Total FGTS Mensal\s+\d+\s+([\d.,]+)', texto)
    fgts_total = m.group(1) if m else "NÃO ENCONTRADO"

    m = re.search(r'Total Descontos Sindicais\s+\d+\s+[\d.,]+\s+([\d.,]+)', texto)
    sindicato = m.group(1) if m else "0,00"

    m = re.search(r'Total CP SEGURADOS\s+([\d.,]+)', texto)
    inss = m.group(1) if m else "NÃO ENCONTRADO"

    m = re.search(r'Total IRRF\s+([\d.,]+)\s+0,00', texto)
    irrf = m.group(1) if m else "NÃO ENCONTRADO"

    return {
        "Codigo_Empresa":   codigo_empresa,
        "Nome_Empresa":     nome_empresa,
        "Qtd_Funcionarios": qtd,
        "Total_Liquido":    liquido,
        "FGTS_11_Mensal":   fgts_11,
        "FGTS_Total_Mensal": fgts_total,
        "Total_Sindicato":  sindicato,
        "INSS_Segurados":   inss,
        "IRRF_Total":       irrf,
    }

# Carrega dados salvos
registros = carregar_dados()

# Upload
arquivo = st.file_uploader("Envie o PDF da folha", type="pdf")

if arquivo:
    with st.spinner("Extraindo dados..."):
        dados = extrair_dados(arquivo)
    registros.append(dados)
    salvar_dados(registros)
    st.success(f"✅ {dados['Nome_Empresa']} adicionado!")

# Mostra tabela acumulada
if registros:
    st.subheader(f"📊 {len(registros)} registro(s) salvos")
    st.table(registros)

    # Botão limpar
    col1, col2 = st.columns(2)

    with col1:
        # Download CSV
        campos = list(registros[0].keys())
        saida = io.StringIO()
        writer = csv.DictWriter(saida, fieldnames=campos, delimiter=";")
        writer.writeheader()
        writer.writerows(registros)
        st.download_button(
            label="⬇️ Baixar CSV completo",
            data=saida.getvalue().encode("utf-8-sig"),
            file_name="folhas.csv",
            mime="text/csv"
        )

    with col2:
        if st.button("🗑️ Limpar tabela"):
            salvar_dados([])
            st.rerun()
else:
    st.info("Nenhum dado ainda. Envie um PDF para começar.")