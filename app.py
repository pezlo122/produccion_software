from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import pandas as pd
import os
import requests
import math

app = Flask(__name__)
app.secret_key = "mi_api_key_segura"

# --- Configuración ---
DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')
USERS_FILE = os.path.join(DATA_PATH, 'users.csv')
API_KEY = "41d18781051e38c1a3a35fa10bfbc9b2"  # ⚠️ Reemplaza esto con tu API Key de TMDB
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# --- Gestión de usuarios ---
def load_users():
    if not os.path.exists(DATA_PATH):
        os.makedirs(DATA_PATH)
    if not os.path.exists(USERS_FILE):
        df = pd.DataFrame(columns=['username', 'password'])
        df.to_csv(USERS_FILE, index=False)
    return pd.read_csv(USERS_FILE)

def register_user(username, password):
    df = load_users()
    if username in df['username'].values:
        return False, "El usuario ya existe."
    new_user = pd.DataFrame([[username, password]], columns=['username', 'password'])
    df = pd.concat([df, new_user], ignore_index=True)
    df.to_csv(USERS_FILE, index=False)
    return True, "Usuario registrado exitosamente."

def verify_user(username, password):
    df = load_users()
    user = df[(df['username'] == username) & (df['password'] == password)]
    return not user.empty

# --- Funciones auxiliares ---
def get_movies(page=1, query=None, genre=None):
    params = {
        "api_key": API_KEY,
        "language": "es-ES",
        "page": page
    }

    # Búsqueda por nombre
    if query:
        url = f"{TMDB_BASE_URL}/search/movie"
        params["query"] = query
    else:
        url = f"{TMDB_BASE_URL}/discover/movie"
        if genre:
            params["with_genres"] = genre

    response = requests.get(url, params=params)
    data = response.json()
    return data

def get_movie_details(movie_id):
    url = f"{TMDB_BASE_URL}/movie/{movie_id}"
    params = {"api_key": API_KEY, "language": "es-ES"}
    response = requests.get(url, params=params)
    return response.json()

def get_recommendations(genre_ids, rating):
    params = {
        "api_key": API_KEY,
        "language": "es-ES",
        "sort_by": "vote_average.desc",
        "with_genres": ",".join(map(str, genre_ids)),
        "vote_average.gte": rating,
        "page": 1
    }
    url = f"{TMDB_BASE_URL}/discover/movie"
    response = requests.get(url, params=params)
    return response.json().get("results", [])

# --- Rutas principales ---
@app.route('/')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('movies'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if verify_user(username, password):
            session['user'] = username
            return redirect(url_for('movies'))
        else:
            flash("Usuario o contraseña incorrectos", "error")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        ok, msg = register_user(username, password)
        flash(msg)
        if ok:
            return redirect(url_for('login'))
    return render_template('register.html')

# --- Listado de películas con búsqueda, filtro y paginación ---
@app.route('/movies')
def movies():
    if 'user' not in session:
        return redirect(url_for('login'))

    page = int(request.args.get('page', 1))
    query = request.args.get('query')
    genre = request.args.get('genre')

    data = get_movies(page, query, genre)
    movies = data.get("results", [])
    total_pages = min(data.get("total_pages", 1), 10)

    return render_template(
        'movies.html',
        movies=movies,
        page=page,
        total_pages=total_pages,
        query=query or "",
        genre=genre or "",
        user=session['user']
    )

# --- Detalle de película y recomendaciones ---
@app.route('/movie/<int:movie_id>')
def movie_detail(movie_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    movie = get_movie_details(movie_id)
    if not movie or "status_code" in movie:
        return "Película no encontrada", 404

    recommendations = get_recommendations(
        [g["id"] for g in movie.get("genres", [])],
        movie.get("vote_average", 0)
    )

    return render_template('movie.html', movie=movie, recommendations=recommendations)

# --- Panel de administración ---
@app.route('/admin')
def admin_panel():
    if 'user' not in session or session['user'] != 'admin':
        return redirect(url_for('movies'))
    users = load_users().to_dict(orient='records')
    return render_template('admin.html', users=users)

# --- Ejecución ---
if __name__ == '__main__':
    app.run(debug=True, port=5000)
