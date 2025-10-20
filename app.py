from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = 'clave_secreta_super_segura'

# --- Rutas de los datos ---
DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')
MOVIES_FILE = os.path.join(DATA_PATH, 'tmdb_5000_movies.csv')
CREDITS_FILE = os.path.join(DATA_PATH, 'tmdb_5000_credits.csv')

_movies_df = None
_credits_df = None

# --- Funciones de carga y autenticación ---
def load_data():
    global _movies_df, _credits_df
    if _movies_df is None or _credits_df is None:
        _movies_df = pd.read_csv(MOVIES_FILE)
        _credits_df = pd.read_csv(CREDITS_FILE)


def ensure_users_file():
    """Crea un archivo de usuarios básico si no existe"""
    users_path = os.path.join(DATA_PATH, 'users.csv')
    if not os.path.exists(users_path):
        with open(users_path, 'w', encoding='utf-8') as f:
            f.write('username,password\nadmin,1234\n')


def verify_credentials(username, password):
    """Verifica credenciales básicas usando users.csv"""
    users_path = os.path.join(DATA_PATH, 'users.csv')
    if not os.path.exists(users_path):
        return False
    df = pd.read_csv(users_path)
    match = df[(df['username'] == username) & (df['password'] == password)]
    return not match.empty


# --- Rutas de la aplicación ---
@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if verify_credentials(username, password):
            session['user'] = username
            return redirect(url_for('dashboard'))
        else:
            flash('Credenciales inválidas', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    load_data()
    total_movies = len(_movies_df)
    return render_template('dashboard.html', user=session['user'], total_movies=total_movies)


@app.route('/movies')
def movies():
    if 'user' not in session:
        return redirect(url_for('login'))
    load_data()
    movies = _movies_df[['id', 'title', 'release_date', 'vote_average']].head(200).to_dict(orient='records')
    return render_template('movies.html', movies=movies)


@app.route('/movie/<int:movie_id>')
def movie_detail(movie_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    load_data()
    m = _movies_df[_movies_df['id'] == movie_id]
    if m.empty:
        return 'Película no encontrada', 404
    m = m.iloc[0].to_dict()
    c = _credits_df[_credits_df['movie_id'] == movie_id]
    credits = c.to_dict(orient='records') if not c.empty else []
    return render_template('movie.html', movie=m, credits=credits)


# --- Endpoints API ---
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json or request.form
    username = data.get('username')
    password = data.get('password')
    ok = verify_credentials(username, password)
    return jsonify({'ok': ok, 'user': username if ok else None})


@app.route('/api/movies')
def api_movies():
    load_data()
    movies = _movies_df[['id', 'title', 'release_date', 'vote_average']].head(500).to_dict(orient='records')
    return jsonify(movies)


# --- Ejecución principal ---
if __name__ == '__main__':
    ensure_users_file()
    load_data()
    app.run(debug=True, port=5000)
