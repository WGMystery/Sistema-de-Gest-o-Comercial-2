from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database.db"

app = Flask(__name__)
app.secret_key = "troque-esta-chave-em-producao"

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            categoria TEXT NOT NULL,
            descricao TEXT DEFAULT '',
            preco REAL NOT NULL CHECK(preco >= 0),
            estoque INTEGER NOT NULL CHECK(estoque >= 0),
            estoque_minimo INTEGER NOT NULL DEFAULT 5 CHECK(estoque_minimo >= 0),
            criado_em TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER NOT NULL,
            quantidade INTEGER NOT NULL CHECK(quantidade > 0),
            preco_unitario REAL NOT NULL,
            total REAL NOT NULL,
            data TEXT NOT NULL,
            FOREIGN KEY(produto_id) REFERENCES produtos(id)
        );
        """)
        count = conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
        if count == 0:
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            conn.executemany(
                """INSERT INTO produtos (nome,categoria,descricao,preco,estoque,estoque_minimo,criado_em)
                   VALUES (?,?,?,?,?,?,?)""",
                [
                    ("Café Tradicional", "Alimentos", "Pacote de café de 500 g", 18.90, 20, 5, now),
                    ("Chá Verde", "Alimentos", "Caixa com 10 sachês", 12.50, 8, 10, now),
                    ("Detergente Neutro", "Limpeza", "Frasco de 500 ml", 3.99, 3, 5, now),
                ]
            )

@app.template_filter("brl")
def brl(value):
    return ("R$ {:,.2f}".format(value or 0)).replace(",", "X").replace(".", ",").replace("X", ".")

@app.route("/")
def index():
    with db() as conn:
        produtos = conn.execute("SELECT * FROM produtos ORDER BY nome").fetchall()
        total_produtos = conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
        baixo = conn.execute("SELECT COUNT(*) FROM produtos WHERE estoque <= estoque_minimo").fetchone()[0]
        vendas_hoje = conn.execute(
            "SELECT COALESCE(SUM(total),0) FROM vendas WHERE date(data)=date('now','localtime')"
        ).fetchone()[0]
        ultimas = conn.execute("""
            SELECT v.*, p.nome AS produto_nome FROM vendas v
            JOIN produtos p ON p.id=v.produto_id ORDER BY v.id DESC LIMIT 5
        """).fetchall()
    return render_template("dashboard.html", produtos=produtos, total_produtos=total_produtos,
                           baixo=baixo, vendas_hoje=vendas_hoje, ultimas=ultimas)

@app.route("/produtos")
def produtos():
    termo = request.args.get("q", "").strip()
    with db() as conn:
        if termo:
            itens = conn.execute("SELECT * FROM produtos WHERE nome LIKE ? OR categoria LIKE ? ORDER BY nome",
                                 (f"%{termo}%", f"%{termo}%")).fetchall()
        else:
            itens = conn.execute("SELECT * FROM produtos ORDER BY nome").fetchall()
    return render_template("produtos.html", produtos=itens, q=termo)

@app.route("/produtos/novo", methods=["GET", "POST"])
def novo_produto():
    if request.method == "POST":
        try:
            nome = request.form["nome"].strip()
            categoria = request.form["categoria"].strip()
            descricao = request.form.get("descricao", "").strip()
            preco = float(request.form["preco"])
            estoque = int(request.form["estoque"])
            minimo = int(request.form.get("estoque_minimo", 5))
            if not nome or not categoria or preco < 0 or estoque < 0 or minimo < 0:
                raise ValueError()
            with db() as conn:
                conn.execute("""INSERT INTO produtos(nome,categoria,descricao,preco,estoque,estoque_minimo,criado_em)
                                VALUES(?,?,?,?,?,?,?)""",
                             (nome,categoria,descricao,preco,estoque,minimo,datetime.now().strftime("%Y-%m-%d %H:%M")))
            flash("Produto cadastrado com sucesso.", "success")
            return redirect(url_for("produtos"))
        except (ValueError, KeyError):
            flash("Confira os campos. Preço e quantidades não podem ser negativos.", "error")
    return render_template("produto_form.html", produto=None)

@app.route("/produtos/<int:produto_id>/editar", methods=["GET", "POST"])
def editar_produto(produto_id):
    with db() as conn:
        produto = conn.execute("SELECT * FROM produtos WHERE id=?", (produto_id,)).fetchone()
        if not produto:
            flash("Produto não encontrado.", "error")
            return redirect(url_for("produtos"))
        if request.method == "POST":
            try:
                nome = request.form["nome"].strip()
                categoria = request.form["categoria"].strip()
                descricao = request.form.get("descricao", "").strip()
                preco = float(request.form["preco"])
                estoque = int(request.form["estoque"])
                minimo = int(request.form.get("estoque_minimo", 5))
                if not nome or not categoria or preco < 0 or estoque < 0 or minimo < 0:
                    raise ValueError()
                conn.execute("""UPDATE produtos SET nome=?,categoria=?,descricao=?,preco=?,estoque=?,estoque_minimo=?
                                WHERE id=?""", (nome,categoria,descricao,preco,estoque,minimo,produto_id))
                flash("Produto atualizado.", "success")
                return redirect(url_for("produtos"))
            except (ValueError, KeyError):
                flash("Dados inválidos. Verifique os campos.", "error")
    return render_template("produto_form.html", produto=produto)

@app.post("/produtos/<int:produto_id>/excluir")
def excluir_produto(produto_id):
    with db() as conn:
        usado = conn.execute("SELECT COUNT(*) FROM vendas WHERE produto_id=?", (produto_id,)).fetchone()[0]
        if usado:
            flash("Este produto possui vendas registradas e não pode ser excluído.", "error")
        else:
            conn.execute("DELETE FROM produtos WHERE id=?", (produto_id,))
            flash("Produto excluído.", "success")
    return redirect(url_for("produtos"))

@app.route("/vendas", methods=["GET", "POST"])
def vendas():
    with db() as conn:
        if request.method == "POST":
            try:
                produto_id = int(request.form["produto_id"])
                quantidade = int(request.form["quantidade"])
                produto = conn.execute("SELECT * FROM produtos WHERE id=?", (produto_id,)).fetchone()
                if not produto or quantidade <= 0:
                    raise ValueError()
                if quantidade > produto["estoque"]:
                    flash("Estoque insuficiente para esta venda.", "error")
                else:
                    total = produto["preco"] * quantidade
                    conn.execute("UPDATE produtos SET estoque=estoque-? WHERE id=?", (quantidade, produto_id))
                    conn.execute("""INSERT INTO vendas(produto_id,quantidade,preco_unitario,total,data)
                                    VALUES(?,?,?,?,?)""",
                                 (produto_id, quantidade, produto["preco"], total, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    flash("Venda registrada e estoque atualizado.", "success")
                    return redirect(url_for("vendas"))
            except (ValueError, KeyError):
                flash("Selecione um produto e informe uma quantidade válida.", "error")
        disponiveis = conn.execute("SELECT * FROM produtos WHERE estoque > 0 ORDER BY nome").fetchall()
        historico = conn.execute("""SELECT v.*, p.nome AS produto_nome FROM vendas v
                                    JOIN produtos p ON p.id=v.produto_id ORDER BY v.id DESC""").fetchall()
    return render_template("vendas.html", produtos=disponiveis, vendas=historico)

@app.route("/estoque")
def estoque():
    with db() as conn:
        itens = conn.execute("SELECT * FROM produtos ORDER BY estoque ASC, nome").fetchall()
    return render_template("estoque.html", produtos=itens)

@app.route("/relatorios")
def relatorios():
    with db() as conn:
        resumo = conn.execute("""SELECT COUNT(*) AS quantidade, COALESCE(SUM(total),0) AS faturamento
                                 FROM vendas""").fetchone()
        por_produto = conn.execute("""SELECT p.nome, SUM(v.quantidade) AS unidades, SUM(v.total) AS total
                                      FROM vendas v JOIN produtos p ON p.id=v.produto_id
                                      GROUP BY p.id ORDER BY total DESC""").fetchall()
    return render_template("relatorios.html", resumo=resumo, por_produto=por_produto)

with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(debug=True)
