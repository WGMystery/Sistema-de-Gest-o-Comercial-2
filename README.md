# Sistema de Gestão Comercial

MVP web para pequenos empreendimentos, desenvolvido com Python, Flask, SQLite, HTML e CSS.

## Funcionalidades
- Painel com indicadores de produtos, estoque baixo e vendas do dia.
- Cadastro, consulta, edição e exclusão de produtos.
- Registro de vendas com baixa automática do estoque.
- Histórico de vendas.
- Alertas de estoque baixo e sem estoque.
- Relatório de vendas por produto.

## Executar localmente
Requer Python 3.12 ou superior.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Abra http://127.0.0.1:5000

O banco SQLite `database.db` é criado automaticamente na primeira execução e recebe alguns registros demonstrativos.

## Publicação
Este projeto usa Flask e precisa de hospedagem que execute Python (por exemplo, Render). GitHub Pages não executa aplicações Flask. Para publicar no Render, conecte o repositório e configure:
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`

Para uso real, configure uma chave secreta própria e armazenamento persistente para o banco SQLite. Os dados demonstrativos são apenas para avaliação do MVP.
