from flask import Flask, render_template, request, redirect, url_for, session, flash
import csv
import os
import requests

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# -------------------------------
# CONFIGURACIÓN DE API Y ARCHIVOS
# -------------------------------
TMDB_API_KEY = "41d18781051e38c1a3a35fa10bfbc9b2"  # 🔹 Tu clave de TMDB
TMDB_BASE_URL = "https://api.themoviedb.org/3"

DATA_FILE = os.path.join('data', 'users.csv')
os.makedirs('data', exist_ok=True)

# -------------------------------
# FUNCIONES AUXILIARES
# -------------------------------
def load_users():
    users = []
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            users = list(reader)
    return users

def save_user(username, email, password):
    file_exists = os.path.exists(DATA_FILE)
    with open(DATA_FILE, 'a', newline='', encoding='utf-8') as f:
        fieldnames = ['username', 'email', 'password']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({'username': username, 'email': email, 'password': password})

def validate_login(identifier, password):
    users = load_users()
    for user in users:
        if (user['username'] == identifier or user['email'] == identifier) and user['password'] == password:
            return True
    return False

def user_exists(username, email):
    """Verifica si ya existe un usuario o correo registrado."""
    users = load_users()
    for user in users:
        if user['username'] == username or user['email'] == email:
            return True
    return False

# -------------------------------
# RUTAS PRINCIPALES
# -------------------------------
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/choose')
def choose():
    return render_template('choose.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if not username or not email or not password:
            flash('Por favor completa todos los campos.', 'error')
            return redirect(url_for('register'))

        if user_exists(username, email):
            flash('El usuario o correo ya están registrados. Intenta con otros.', 'error')
            return redirect(url_for('register'))

        save_user(username, email, password)
        flash('✅ Registro exitoso. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['username']
        password = request.form['password']

        if validate_login(identifier, password):
            session['user_id'] = identifier
            return redirect(url_for('dashboard'))
        else:
            flash('❌ Credenciales inválidas. Intenta de nuevo.', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# -------------------------------
# CATÁLOGO DE PELÍCULAS
# -------------------------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    search_query = request.args.get('query', '')
    genre_id = request.args.get('genre', '')
    page = int(request.args.get('page', 1))

    params = {
        "api_key": TMDB_API_KEY,
        "language": "es-ES",
        "sort_by": "popularity.desc",
        "page": page
    }

    if search_query:
        response = requests.get(f"{TMDB_BASE_URL}/search/movie", params={**params, "query": search_query})
    else:
        response = requests.get(f"{TMDB_BASE_URL}/discover/movie", params=params)

    movies = response.json().get('results', [])

    # Obtener géneros
    genres_resp = requests.get(f"{TMDB_BASE_URL}/genre/movie/list", params={"api_key": TMDB_API_KEY, "language": "es-ES"})
    genres = genres_resp.json().get('genres', [])

    # Filtrar por género
    if genre_id:
        movies = [m for m in movies if genre_id in map(str, m.get('genre_ids', []))]

    next_page = page + 1
    prev_page = page - 1 if page > 1 else None

    return render_template('dashboard.html',
                           movies=movies,
                           genres=genres,
                           search_query=search_query,
                           genre_id=genre_id,
                           current_page=page,
                           next_page=next_page,
                           prev_page=prev_page)

# -------------------------------
# DETALLE DE PELÍCULA
# -------------------------------
@app.route('/movie/<int:movie_id>')
def movie(movie_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    response = requests.get(f"{TMDB_BASE_URL}/movie/{movie_id}", params={"api_key": TMDB_API_KEY, "language": "es-ES"})
    movie = response.json()

    rec_response = requests.get(f"{TMDB_BASE_URL}/movie/{movie_id}/recommendations", params={"api_key": TMDB_API_KEY, "language": "es-ES"})
    recommendations = rec_response.json().get('results', [])

    return render_template('movie.html', movie=movie, recommendations=recommendations)

# -------------------------------
# EJECUCIÓN
# -------------------------------
if __name__ == '__main__':
    app.run(debug=True)
