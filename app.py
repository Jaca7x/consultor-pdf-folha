import streamlit as st
import pdfplumber
import re
import csv
import io
import json
import os
import hashlib

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

    # 1. Empresa (Código e Nome)
    m = re.search(r'Empresa:\s*(\d+)\s*-\s*(.+?)\s+\d{2}/\d{2}/\d{4}', texto)
    codigo_empresa = m.group(1).strip() if m else "NÃO ENCONTRADO"
    nome_empresa   = m.group(2).strip() if m else "NÃO ENCONTRADO"

    # 2. Quantidade de Funcionários
    m = re.search(r'1 - Empregado\s+(\d+)', texto)
    qtd = m.group(1) if m else "0"

    # 3. Total Líquido
    m = re.search(r'Totais\s*\n\s*Proventos:.*?L[íi]quido:\s*([\d.,]+)', texto, re.DOTALL)
    liquido = m.group(1) if m else "0,00"

    # 4. FGTS 11 (Lógica para pegar o SEGUNDO/ÚLTIMO valor "11 - FGTS mensal")
    # findall retorna uma lista com todos os valores encontrados
    matches_fgts_11 = re.findall(r'11 - FGTS mensal\s+([\d.,]+)', texto)
    # Pegamos o índice [-1] que é sempre o último (o da Guia Mensal)
    fgts_11 = matches_fgts_11[-1] if matches_fgts_11 else "0,00"

    # Outros campos de FGTS
    m_fgts_cons = re.search(r'Empr[eé]stimo Cr[eé]dito do Trabalhador\s+\d+\s+([\d.,]+)', texto)
    fgts_consignado = m_fgts_cons.group(1) if m_fgts_cons else "0,00"

    m_fgts_total = re.search(r'Total FGTS Mensal\s+\d+\s+([\d.,]+)', texto)
    fgts_total = m_fgts_total.group(1) if m_fgts_total else "0,00"

    # 5. INSS (Total da seção Resumo Contribuições)
    m_inss = re.search(r'Resumo Contribui[çc][õo]es.*?Total:\s+([\d.,]+)', texto, re.DOTALL)
    inss = m_inss.group(1) if m_inss else "0,00"

    # 6. IRRF (Total da seção Resumo IRRF)
    m_irrf = re.search(r'Resumo IRRF.*?Total IRRF\s+[\d.,]+\s+([\d.,]+)', texto, re.DOTALL)
    irrf = m_irrf.group(1) if m_irrf else "0,00"

    # 7. Total DCTFWeb (Saldo a Pagar da seção Demonstrativo DCTFWeb)
    m_dctf = re.search(r'Total EMPRESA:.*?([\d.,]+)$', texto, re.MULTILINE)
    dctf = m_dctf.group(1) if m_dctf else "0,00"

    return {
        "Codigo_Empresa":   codigo_empresa,
        "Nome_Empresa":     nome_empresa,
        "Qtd_Funcionarios": qtd,
        "Total_Liquido":    liquido,
        "FGTS_11_Mensal":   fgts_11,
        "FGTS_Consignado":  fgts_consignado,
        "FGTS_Total_Mensal": fgts_total,
        "INSS_Segurados":   inss,
        "IRRF_Total":       irrf,
        "Total_DCTFWeb":    dctf,
    }

# --- Interface Streamlit ---

registros = carregar_dados()

arquivo = st.file_uploader("Selecione o PDF da Folha", type=["pdf"])

if arquivo:
    conteudo = arquivo.read()
    arquivo.seek(0)
    hash_arquivo = hashlib.md5(conteudo).hexdigest()

    if "ultimo_hash" not in st.session_state or st.session_state.ultimo_hash != hash_arquivo:
        with st.spinner("Extraindo dados..."):
            dados = extrair_dados(arquivo)
        
        # Verifica se já existe para não duplicar na mesma lista
        if not any(r['Codigo_Empresa'] == dados['Codigo_Empresa'] for r in registros):
            registros.append(dados)
            salvar_dados(registros)
            st.success(f"✅ Empresa {dados['Nome_Empresa']} adicionada!")
        else:
            st.warning("Esta empresa já foi processada.")
        
        st.session_state.ultimo_hash = hash_arquivo

if registros:
    st.subheader(f"📊 {len(registros)} Registro(s)")
    st.table(registros)

    col1, col2 = st.columns(2)
    with col1:
        campos = [
            "Codigo_Empresa", "Nome_Empresa", "Qtd_Funcionarios",
            "Total_Liquido", "FGTS_11_Mensal", "FGTS_Consignado",
            "FGTS_Total_Mensal", "INSS_Segurados", "IRRF_Total", "Total_DCTFWeb"
        ]
        saida = io.StringIO()
        writer = csv.DictWriter(saida, fieldnames=campos, delimiter=";", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(registros)
        st.download_button("⬇️ Baixar CSV", saida.getvalue().encode("utf-8-sig"), "folhas.csv", "text/csv")

    with col2:
        if st.button("🗑️ Limpar Tabela"):
            salvar_dados([])
            st.rerun()
else:
    st.info("Aguardando envio de arquivo PDF para extração.")