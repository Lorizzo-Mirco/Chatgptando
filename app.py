from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'la_tua_chiave_segreta'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///capsules.db'
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Modello per gli utenti
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)

# Modello per le capsule del tempo
class Capsule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    release_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    photo_path = db.Column(db.String(300), nullable=True)
    video_path = db.Column(db.String(300), nullable=True)
    link = db.Column(db.String(300), nullable=True)
    name = db.Column(db.String(80), nullable=False)

    def __repr__(self):
        return f'<Capsule {self.name}>'

class CapsuleManager:
    def __init__(self):
        self.viewed_capsules = []

    def add_viewed_capsule(self, capsule):
        self.viewed_capsules.append(capsule)

    def remove_viewed_capsule(self, capsule_id):
        self.viewed_capsules = [capsule for capsule in self.viewed_capsules if capsule.id != capsule_id]

# Esempio di utilizzo
capsule1 = Capsule(id=1, name="Capsula 1", user_id=1, content="Contenuto 1", release_date=datetime.utcnow())
capsule2 = Capsule(id=2, name="Capsula 2", user_id=1, content="Contenuto 2", release_date=datetime.utcnow())

manager = CapsuleManager()
manager.add_viewed_capsule(capsule1)
manager.add_viewed_capsule(capsule2)

print("Capsule viste prima della rimozione:", [capsule.name for capsule in manager.viewed_capsules])

manager.remove_viewed_capsule(1)

print("Capsule viste dopo la rimozione:", [capsule.name for capsule in manager.viewed_capsules])

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Home page: pagina iniziale con informazioni sul sito
@app.route('/')
def home():
    return render_template('home.html')

# Route di registrazione
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            flash('Username già esistente!')
            return redirect(url_for('register'))
        new_user = User(username=username, password_hash=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('dashboard'))
    return render_template('register.html')

# Route di login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Credenziali non valide')
    return render_template('login.html')

# Route di logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Dashboard dell'utente: mostra le capsule create
@app.route('/dashboard')
@login_required
def dashboard():
    capsules = Capsule.query.all()
    return render_template('dashboard.html', capsules=capsules)

# Creazione di una nuova capsule
@app.route('/capsule/new', methods=['GET', 'POST'])
@login_required
def new_capsule():
    if request.method == 'POST':
        content = request.form.get('content')
        release_date_str = request.form.get('release_date')  # Formato atteso: YYYY-MM-DD
        link = request.form.get('link')
        photo = request.files.get('photo')
        video = request.files.get('video')

        try:
            release_date = datetime.strptime(release_date_str, '%d-%m-%Y')
        except ValueError:
            flash("Formato data non valido, usa DD-MM-YYYY")
            return redirect(url_for('new_capsule'))

        photo_path, video_path = None, None

        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(path)
            photo_path = path

        if video and video.filename:
            video_filename = secure_filename(video.filename)
            video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_filename)
            video.save(video_path)

        new_capsule = Capsule(user_id=current_user.id, content=content, release_date=release_date, photo_path=photo_path, video_path=video_path, link=link, name="New Capsule")
        db.session.add(new_capsule)
        db.session.commit()
        flash("Capsula creata con successo!")
        return redirect(url_for('dashboard'))
    return render_template('new_capsule.html')

# Visualizza una capsule (solo se è "aperta")
@app.route('/capsule/<int:capsule_id>')
@login_required
def view_capsule(capsule_id):
    capsule = Capsule.query.get_or_404(capsule_id)
    if capsule.user_id != current_user.id:
        flash("Non sei autorizzato a visualizzare questa capsule.")
        return redirect(url_for('dashboard'))
    if datetime.utcnow() >= capsule.release_date:
        # La capsule è aperta
        return render_template('view_capsule.html', capsule=capsule)
    else:
        flash(f"La capsule sarà disponibile il {capsule.release_date.strftime('%Y-%m-%d')}.")
        return redirect(url_for('dashboard'))

@app.route('/view_capsule/<int:capsule_id>', endpoint='view_capsule_endpoint')
def view_capsule_by_id(capsule_id):
    capsule = Capsule.query.get_or_404(capsule_id)
    return render_template('view_capsule.html', capsule=capsule)

@app.route('/capsules')
def get_capsules():
    capsules = Capsule.query.all()
    return {'capsules': [capsule.name for capsule in capsules]}

@app.route('/capsules/delete/<int:capsule_id>', methods=['POST'])
def remove_capsule(capsule_id):
    capsule = Capsule.query.get_or_404(capsule_id)
    db.session.delete(capsule)
    db.session.commit()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)