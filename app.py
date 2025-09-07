
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
import os
import csv
import json
from datetime import datetime

# Configuración básica
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATOS_DIR = os.path.join(BASE_DIR, 'datos')
DB_DIR = os.path.join(BASE_DIR, 'database')
if not os.path.exists(DATOS_DIR):
    os.makedirs(DATOS_DIR)
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cambiar-esta-clave-por-una-segura'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(DB_DIR, 'usuarios.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modelo de ejemplo para SQLite
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=False, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'email': self.email,
            'fecha': self.fecha.isoformat()
        }

# Inicializar la base de datos si no existe
with app.app_context():
    db.create_all()

# Rutas principales
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        if not nombre or not email:
            flash('Nombre y email son obligatorios', 'danger')
            return redirect(url_for('formulario'))

        # 1) Guardar en TXT
        txt_path = os.path.join(DATOS_DIR, 'datos.txt')
        with open(txt_path, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.utcnow().isoformat()}|{nombre}|{email}\n")

        # 2) Guardar en JSON (append al arreglo)
        json_path = os.path.join(DATOS_DIR, 'datos.json')
        entry = {'timestamp': datetime.utcnow().isoformat(), 'nombre': nombre, 'email': email}
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as jf:
                try:
                    data = json.load(jf)
                except Exception:
                    data = []
        else:
            data = []
        data.append(entry)
        with open(json_path, 'w', encoding='utf-8') as jf:
            json.dump(data, jf, ensure_ascii=False, indent=2)

        # 3) Guardar en CSV
        csv_path = os.path.join(DATOS_DIR, 'datos.csv')
        file_exists = os.path.exists(csv_path)
        with open(csv_path, 'a', newline='', encoding='utf-8') as cf:
            writer = csv.writer(cf)
            if not file_exists:
                writer.writerow(['timestamp', 'nombre', 'email'])
            writer.writerow([datetime.utcnow().isoformat(), nombre, email])

        # 4) Guardar en SQLite
        usuario = Usuario(nombre=nombre, email=email)
        db.session.add(usuario)
        db.session.commit()

        return redirect(url_for('resultado', usuario_id=usuario.id))

    return render_template('formulario.html')

@app.route('/resultado/<int:usuario_id>')
def resultado(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    return render_template('resultado.html', usuario=usuario)

# Rutas para leer los datos desde archivos
@app.route('/leer_txt')
def leer_txt():
    txt_path = os.path.join(DATOS_DIR, 'datos.txt')
    registros = []
    if os.path.exists(txt_path):
        with open(txt_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split('|')
                if len(parts) >= 3:
                    registros.append({'timestamp': parts[0], 'nombre': parts[1], 'email': parts[2]})
    return jsonify(registros)

@app.route('/leer_json')
def leer_json():
    json_path = os.path.join(DATOS_DIR, 'datos.json')
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as jf:
            try:
                data = json.load(jf)
            except Exception:
                data = []
    else:
        data = []
    return jsonify(data)

@app.route('/leer_csv')
def leer_csv():
    csv_path = os.path.join(DATOS_DIR, 'datos.csv')
    registros = []
    if os.path.exists(csv_path):
        with open(csv_path, 'r', encoding='utf-8') as cf:
            reader = csv.DictReader(cf)
            for row in reader:
                registros.append(row)
    return jsonify(registros)

# Rutas para gestionar usuarios en SQLite (API simple)
@app.route('/usuarios', methods=['GET'])
def listar_usuarios():
    usuarios = Usuario.query.order_by(Usuario.fecha.desc()).all()
    return jsonify([u.to_dict() for u in usuarios])

@app.route('/usuarios/<int:uid>', methods=['GET'])
def obtener_usuario(uid):
    u = Usuario.query.get_or_404(uid)
    return jsonify(u.to_dict())

@app.route('/usuarios', methods=['POST'])
def crear_usuario_api():
    data = request.get_json() or {}
    nombre = data.get('nombre')
    email = data.get('email')
    if not nombre or not email:
        return jsonify({'error': 'nombre y email son requeridos'}), 400
    u = Usuario(nombre=nombre, email=email)
    db.session.add(u)
    db.session.commit()
    return jsonify(u.to_dict()), 201

if __name__ == '__main__':
    app.run(debug=True)
