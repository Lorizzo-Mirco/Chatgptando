from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'la_tua_chiave_segreta'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///time_capsule.db'
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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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
    capsules = Capsule.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', capsules=capsules, now=datetime.utcnow())

# Creazione di una nuova capsule
@app.route('/capsule/new', methods=['GET', 'POST'])
@login_required
def new_capsule():
    if request.method == 'POST':
        content = request.form.get('content')
        release_date_str = request.form.get('release_date')  # Formato atteso: YYYY-MM-DD
        try:
            release_date = datetime.strptime(release_date_str, '%Y-%m-%d')
        except ValueError:
            flash('Formato data non valido. Usa YYYY-MM-DD.')
            return redirect(url_for('new_capsule'))
        new_capsule = Capsule(user_id=current_user.id, content=content, release_date=release_date)
        db.session.add(new_capsule)
        db.session.commit()
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

if __name__ == '__main__':
    # Creare il database (solo la prima volta)
    with app.app_context():
        db.create_all()
    app.run(debug=True)
