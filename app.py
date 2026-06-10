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

# --- Funções de Conversão ---
def str_para_float(valor_str):
    if not valor_str:
        return 0.0
    return float(valor_str.replace('.', '').replace(',', '.'))

def float_para_str(valor_float):
    return f"{valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

# --- Persistência de Dados ---
def carregar_dados():
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def salvar_dados(dados):
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

# --- Extração de Dados ---
def extrair_dados(arquivo):
    with pdfplumber.open(arquivo) as pdf:
        paginas = [p.extract_text() or "" for p in pdf.pages]
    texto = "\n".join(paginas)

    # 1. Empresa
    m = re.search(r'Empresa:\s*(\d+)\s*-\s*(.+?)\s+\d{2}/\d{2}/\d{4}', texto)
    codigo_empresa = m.group(1).strip() if m else "NÃO ENCONTRADO"
    nome_empresa   = m.group(2).strip() if m else "NÃO ENCONTRADO"

    # 2. Qtd Funcionários
    m = re.search(r'1 - Empregado\s+(\d+)', texto)
    qtd = m.group(1) if m else "0"

    # 3. Total Líquido
    m = re.search(r'Totais\s*\n\s*Proventos:.*?L[íi]quido:\s*([\d.,]+)', texto, re.DOTALL)
    liquido = m.group(1) if m else "0,00"

    # 4. FGTS (Soma Código 11 + Código 12)
    matches_11 = re.findall(r'11\s*-\s*FGTS mensal\s+([\d.,]+)', texto)
    valor_11 = str_para_float(matches_11[-1]) if matches_11 else 0.0

    matches_12 = re.findall(r'12\s*-\s*FGTS\s*13[°º].*?\s+([\d.,]+)', texto)
    valor_12 = str_para_float(matches_12[-1]) if matches_12 else 0.0

    fgts_11_somado = float_para_str(valor_11 + valor_12)

    m_fgts_total = re.search(r'Total FGTS Mensal\s+\d+\s+([\d.,]+)', texto)
    fgts_total = m_fgts_total.group(1) if m_fgts_total else "0,00"

    # 5. INSS (Pegando do Resumo Contribuições)
    m_inss = re.search(r'Resumo Contribui[çc][õo]es.*?Total:\s+([\d.,]+)', texto, re.DOTALL)
    inss = m_inss.group(1) if m_inss else "0,00"

    # 6. IRRF (Pegando do Demonstrativo DCTFWeb - Saldo a Pagar)
    m_irrf = re.search(r'Total IRRF\s+[\d.,]+\s+[\d.,]+\s+[\d.,]+\s+[\d.,]+\s+[\d.,]+\s+[\d.,]+\s+([\d.,]+)', texto)
    irrf = m_irrf.group(1) if m_irrf else "0,00"

    # 7. Total DCTFWeb (Saldo a Pagar Total da Empresa)
    m_dctf = re.search(r'Total EMPRESA:.*?([\d.,]+)$', texto, re.MULTILINE)
    dctf = m_dctf.group(1) if m_dctf else "0,00"

    # 8. Sindicato (Total Descontos Sindicais)
    m_sind = re.search(r'Total Descontos Sindicais\s+\d+\s+[\d.,]+\s+([\d.,]+)', texto)
    sindicato = m_sind.group(1) if m_sind else "0,00"

    return {
        "Codigo_Empresa":   codigo_empresa,
        "Nome_Empresa":     nome_empresa,
        "Qtd_Funcionarios": qtd,
        "Total_Liquido":    liquido,
        "FGTS_11_Somado":   fgts_11_somado,
        "FGTS_Total":       fgts_total,
        "INSS":             inss,
        "IRRF":             irrf,
        "Total_Sindicato":  sindicato, # Campo restaurado
        "DCTFWeb":          dctf,
    }

# --- Interface Streamlit ---
registros = carregar_dados()
arquivo = st.file_uploader("Arraste o PDF da Folha aqui", type=["pdf"])

if arquivo:
    conteudo = arquivo.read()
    arquivo.seek(0)
    hash_arquivo = hashlib.md5(conteudo).hexdigest()

    if "ultimo_hash" not in st.session_state or st.session_state.ultimo_hash != hash_arquivo:
        dados = extrair_dados(arquivo)
        if not any(r['Codigo_Empresa'] == dados['Codigo_Empresa'] for r in registros):
            registros.append(dados)
            salvar_dados(registros)
            st.success(f"✅ Extraído: {dados['Nome_Empresa']}")
        st.session_state.ultimo_hash = hash_arquivo

if registros:
    st.subheader("📊 Empresas Processadas")
    st.table(registros)

    col1, col2 = st.columns(2)
    
    with col1:
        # Colunas na ordem para o CSV
        campos = [
            "Codigo_Empresa", "Nome_Empresa", "Qtd_Funcionarios", 
            "Total_Liquido", "FGTS_11_Somado", "FGTS_Total", 
            "INSS", "IRRF", "Total_Sindicato", "DCTFWeb"
        ]
        
        saida = io.StringIO()
        # extrasaction="ignore" evita erros com dados de colunas antigas que você possa ter no banco
        writer = csv.DictWriter(saida, fieldnames=campos, delimiter=";", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(registros)
        
        st.download_button(
            label="⬇️ Baixar CSV Completo",
            data=saida.getvalue().encode("utf-8-sig"),
            file_name="folha_relatorio.csv",
            mime="text/csv"
        )

    with col2:
        if st.button("🗑️ Limpar Tabela"):
            salvar_dados([])
            st.rerun()