
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import pandas as pd
import os
import json

app = Flask(__name__)
app.secret_key = 'clave_secreta_super_segura'

# --- Rutas de los datos ---
DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')
MOVIES_FILE = os.path.join(DATA_PATH, 'tmdb_5000_movies.csv')
CREDITS_FILE = os.path.join(DATA_PATH, 'tmdb_5000_credits.csv')
USERS_FILE = os.path.join(DATA_PATH, 'users.csv')

_movies_df = None
_credits_df = None

def ensure_users_file():
    if not os.path.exists(USERS_FILE):
        os.makedirs(DATA_PATH, exist_ok=True)
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            f.write('username,password\\nadmin,admin123\\n')

def load_data():
    global _movies_df, _credits_df
    if _movies_df is None:
        _movies_df = pd.read_csv(MOVIES_FILE)
        # If poster_path exists, create poster_url; otherwise create placeholder
        if 'poster_path' in _movies_df.columns:
            _movies_df['poster_url'] = _movies_df['poster_path'].apply(
                lambda p: f'https://image.tmdb.org/t/p/w200{p}' if pd.notna(p) and str(p).strip()!='' else '/static/placeholder.png')
        else:
            # fallback placeholder (you can replace with real URLs in the CSV)
            _movies_df['poster_url'] = '/static/placeholder.png'
    if _credits_df is None:
        _credits_df = pd.read_csv(CREDITS_FILE)
        # Parse the cast and crew JSON strings into Python objects
        def safe_parse(s):
            if pd.isna(s):
                return []
            try:
                # Some fields have double quotes escaped; use json.loads after replacing single quotes if necessary
                return json.loads(s)
            except Exception:
                try:
                    return json.loads(s.replace("'", '"'))
                except Exception:
                    return []
        # Ensure columns named 'movie_id' or 'id' map to movie id
        if 'movie_id' in _credits_df.columns:
            _credits_df['movie_id'] = _credits_df['movie_id']
        elif 'id' in _credits_df.columns:
            _credits_df['movie_id'] = _credits_df['id']
        # parse cast and crew
        if 'cast' in _credits_df.columns:
            _credits_df['cast_parsed'] = _credits_df['cast'].apply(safe_parse)
        else:
            _credits_df['cast_parsed'] = [[]]*len(_credits_df)
        if 'crew' in _credits_df.columns:
            _credits_df['crew_parsed'] = _credits_df['crew'].apply(safe_parse)
        else:
            _credits_df['crew_parsed'] = [[]]*len(_credits_df)

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('movies'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    ensure_users_file()
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        users = pd.read_csv(USERS_FILE)
        match = users[(users['username']==username) & (users['password']==password)]
        if not match.empty:
            session['username']=username
            flash('Inicio de sesión exitoso','success')
            return redirect(url_for('movies'))
        else:
            flash('Usuario o contraseña incorrectos','danger')
    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    ensure_users_file()
    if request.method=='POST':
        username=request.form['username'].strip()
        password=request.form['password']
        if not username or not password:
            flash('Usuario y contraseña son obligatorios','warning')
            return redirect(url_for('register'))
        users = pd.read_csv(USERS_FILE)
        if username in users['username'].values:
            flash('El usuario ya existe','warning')
            return redirect(url_for('register'))
        # append to file
        with open(USERS_FILE,'a',encoding='utf-8') as f:
            f.write(f'\\n{username},{password}')
        flash('Registro exitoso. Puedes iniciar sesión.','success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Sesión cerrada','info')
    return redirect(url_for('login'))

@app.route('/movies')
def movies():
    if 'username' not in session:
        return redirect(url_for('login'))
    load_data()
    movies = _movies_df[['id','title','release_date','vote_average','poster_url']].head(500).to_dict(orient='records')
    return render_template('movies.html', movies=movies)

@app.route('/movie/<int:movie_id>')
def movie_detail(movie_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    load_data()
    movie = _movies_df[_movies_df['id']==movie_id]
    if movie.empty:
        flash('Película no encontrada','warning')
        return redirect(url_for('movies'))
    movie = movie.iloc[0].to_dict()
    credits_row = _credits_df[_credits_df['movie_id']==movie_id]
    credits=[]
    if not credits_row.empty:
        cr = credits_row.iloc[0]
        # prepare readable credits: top 10 cast names and key crew jobs
        cast_list = cr.get('cast_parsed', [])[:10]
        credits = [{'type':'cast','name':c.get('name',''), 'character': c.get('character','')} for c in cast_list]
        crew_list = cr.get('crew_parsed', [])
        # pick director(s) and writer(s)
        crew_filtered = [c for c in crew_list if c.get('job') in ('Director','Screenplay','Writer','Editor')][:10]
        for c in crew_filtered:
            credits.append({'type':'crew','job':c.get('job',''),'name':c.get('name','')})
    return render_template('movie.html', movie=movie, credits=credits)

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
