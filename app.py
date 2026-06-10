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

    m = re.search(r'Empr[eé]stimo Cr[eé]dito do Trabalhador\s+\d+\s+([\d.,]+)', texto)
    fgts_consignado = m.group(1) if m else ""

    m = re.search(r'Total FGTS Mensal\s+\d+\s+([\d.,]+)', texto)
    fgts_total = m.group(1) if m else "NÃO ENCONTRADO"

    m = re.search(r'Total Descontos Sindicais\s+\d+\s+[\d.,]+\s+([\d.,]+)', texto)
    sindicato = m.group(1) if m else ""

    m = re.search(r'Total CP SEGURADOS\s+([\d.,]+)', texto)
    inss = m.group(1) if m else "NÃO ENCONTRADO"

    m = re.search(r'Total IRRF\s+([\d.,]+)\s+0,00', texto)
    irrf = m.group(1) if m else "NÃO ENCONTRADO"

    m = re.search(r'Total EMPRESA:[\d./\-]+\s+([\d.,]+)', texto)
    dctf = m.group(1) if m else "NÃO ENCONTRADO"

    return {
        "Codigo_Empresa":   codigo_empresa,
        "Nome_Empresa":     nome_empresa,
        "Qtd_Funcionarios": qtd,
        "Total_Liquido":    liquido,
        "FGTS_11_Mensal":   fgts_11,
        "FGTS_Consignado":  fgts_consignado,
        "FGTS_Total_Mensal": fgts_total,
        "Total_Sindicato":  sindicato,
        "INSS_Segurados":   inss,
        "IRRF_Total":       irrf,
        "Total_DCTFWeb":    dctf,
    }

# Carrega dados salvos
registros = carregar_dados()

# Upload
arquivo = st.file_uploader("Envie o PDF da folha", type="pdf")

if arquivo:
    import hashlib
    conteudo = arquivo.read()
    arquivo.seek(0)
    hash_arquivo = hashlib.md5(conteudo).hexdigest()

    if "ultimo_hash" not in st.session_state or st.session_state.ultimo_hash != hash_arquivo:
        with st.spinner("Extraindo dados..."):
            dados = extrair_dados(arquivo)
        registros.append(dados)
        salvar_dados(registros)
        st.session_state.ultimo_hash = hash_arquivo
        st.success(f"✅ {dados['Nome_Empresa']} adicionado!")
    else:
        st.info("Arquivo já processado. Envie outro PDF.")

# Mostra tabela acumulada
if registros:
    st.subheader(f"📊 {len(registros)} registro(s) salvos")
    st.table(registros)

    # Botão limpar
    col1, col2 = st.columns(2)

    with col1:
        # Download CSV — garante colunas fixas independente de registros antigos
        campos = [
            "Codigo_Empresa", "Nome_Empresa", "Qtd_Funcionarios",
            "Total_Liquido", "FGTS_11_Mensal", "FGTS_Consignado",
            "FGTS_Total_Mensal", "Total_Sindicato", "INSS_Segurados",
            "IRRF_Total", "Total_DCTFWeb"
        ]
        saida = io.StringIO()
        writer = csv.DictWriter(saida, fieldnames=campos, delimiter=";", extrasaction="ignore")
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