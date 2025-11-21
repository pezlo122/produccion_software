import tkinter as tk
from tkinter import messagebox, simpledialog
import requests


API = 'http://127.0.0.1:5000'


class App(tk.Tk):
def __init__(self):
super().__init__()
self.title('TMDB Desktop Client')
self.geometry('700x500')
self.create_widgets()


def create_widgets(self):
self.login_btn = tk.Button(self, text='Login', command=self.login)
self.login_btn.pack(pady=8)
self.listbox = tk.Listbox(self, width=100)
self.listbox.pack(fill='both', expand=True)


def login(self):
username = simpledialog.askstring('Usuario', 'Usuario:')
password = simpledialog.askstring('Contraseña', 'Contraseña:', show='*')
if not username or not password:
return
r = requests.post(API + '/api/login', json={'username':username,'password':password})
if r.ok and r.json().get('ok'):
messagebox.showinfo('OK','Login correcto')
self.load_movies()
else:
messagebox.showerror('Error','Login fallido')


def load_movies(self):
r = requests.get(API + '/api/movies')
if r.ok:
self.listbox.delete(0, tk.END)
for m in r.json():
self.listbox.insert(tk.END, f"{m['id']} - {m['title']} ({m.get('release_date')})")
else:
messagebox.showerror('Error','No se pudieron obtener películas')


if __name__ == '__main__':
app = App()
app.mainloop()