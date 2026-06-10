"""
Instalar dependências (uma vez só):
  pip install flask pdfplumber

Rodar:
  python app.py

Depois abrir no navegador: http://localhost:5000
"""

from flask import Flask, request, send_file, render_template_string
import pdfplumber
import re
import csv
import io

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
  <meta charset="UTF-8">
  <title>Extrator de Folha</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 500px; margin: 80px auto; text-align: center; }
    h1 { font-size: 22px; margin-bottom: 8px; }
    p { color: #666; margin-bottom: 30px; }
    input[type=file] { display: none; }
    label {
      display: inline-block; padding: 12px 28px;
      background: #2563eb; color: white;
      border-radius: 8px; cursor: pointer; font-size: 15px;
    }
    label:hover { background: #1d4ed8; }
    button {
      margin-top: 16px; display: block; width: 100%;
      padding: 12px; background: #16a34a; color: white;
      border: none; border-radius: 8px; font-size: 15px; cursor: pointer;
    }
    button:hover { background: #15803d; }
    #nome { margin-top: 10px; color: #333; font-size: 14px; }
    .erro { color: red; margin-top: 20px; }
  </style>
</head>
<body>
  <h1>Extrator de Folha de Pagamento</h1>
  <p>Envie o PDF e baixe o CSV com os dados principais.</p>
  <form method="POST" enctype="multipart/form-data">
    <label for="pdf">📄 Escolher PDF</label>
    <input type="file" id="pdf" name="pdf" accept=".pdf" onchange="document.getElementById('nome').innerText = this.files[0].name">
    <div id="nome">Nenhum arquivo selecionado</div>
    <button type="submit">⬇️ Extrair e Baixar CSV</button>
  </form>
  {% if erro %}<div class="erro">{{ erro }}</div>{% endif %}
</body>
</html>
"""

def extrair_dados(arquivo):
    with pdfplumber.open(arquivo) as pdf:
        paginas = [p.extract_text() or "" for p in pdf.pages]
    texto = "\n".join(paginas)

    m = re.search(r'Empresa:\s*\d+ - (.+)', texto)
    empresa = m.group(1).strip() if m else "NÃO ENCONTRADO"

    m = re.search(r'Total Funcion[aá]rios\s+(\d+)', texto)
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
        "Empresa": empresa,
        "Qtd_Funcionarios": qtd,
        "Total_Liquido": liquido,
        "INSS_Segurados": inss,
        "IRRF_Total": irrf,
        "FGTS_Mensal": fgts,
    }

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        arquivo = request.files.get("pdf")
        if not arquivo or not arquivo.filename.endswith(".pdf"):
            return render_template_string(HTML, erro="Envie um arquivo PDF válido.")
        try:
            dados = extrair_dados(arquivo)
            saida = io.StringIO()
            writer = csv.DictWriter(saida, fieldnames=dados.keys(), delimiter=";")
            writer.writeheader()
            writer.writerow(dados)
            saida.seek(0)
            return send_file(
                io.BytesIO(saida.getvalue().encode("utf-8-sig")),
                mimetype="text/csv",
                as_attachment=True,
                download_name="folha.csv"
            )
        except Exception as e:
            return render_template_string(HTML, erro=f"Erro ao processar: {e}")
    return render_template_string(HTML, erro=None)

if __name__ == "__main__":
 import os
app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))