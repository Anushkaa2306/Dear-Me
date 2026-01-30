import os
import google.generativeai as genai
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timezone

@app.route('/analyze/<int:id>')
@login_required
def analyze_entry(id):
    entry = DiaryEntry.query.get_or_404(id)
    if entry.user_id != current_user.id:
        return redirect(url_for('index'))

    prompt = f"""
    You are the 'Chronos AI' mentor. Analyze this diary entry: "{entry.content}"
    Provide a brief summary, a motivational insight, and one futuristic quote.
    Tone: Empathetic, encouraging, and Cyber-Pink themed.
    """     
    
    try:
        response = ai_model.generate_content(prompt)
        # We'll flash the AI's response to the UI
        flash(response.text, "ai_glow")
    except Exception as e:
        flash("AI link unstable. Check API key.", "error")
        
    return redirect(url_for('diary'))
# Configure AI Core
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
ai_model = genai.GenerativeModel('gemini-1.5-flash')
app = Flask(__name__)
app.secret_key = "chronos_vault_ultra_secret"

# 1. DATABASE CONFIG
if os.environ.get('DATABASE_URL'):
    database_url = os.environ.get('DATABASE_URL').replace("postgres://", "postgresql://", 1)
else:
    database_url = 'sqlite:///chronos.db'

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 2. UPLOAD CONFIG
UPLOAD_FOLDER = 'static/profile_pics'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 

db = SQLAlchemy(app)

# 3. MODELS (Must be defined before db.create_all())
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    profile_pic = db.Column(db.String(200), nullable=True, default='default_avatar.png')
    capsules = db.relationship('Capsule', backref='owner', lazy=True)
    diary_entries = db.relationship('DiaryEntry', backref='owner', lazy=True)

class Capsule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    unlock_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class DiaryEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# 4. INITIALIZE TABLES
with app.app_context():
    try:
        db.create_all()
        print("Database tables initialized!")
    except Exception as e:
        print(f"Database error: {e}")

# 5. LOGIN MANAGER
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ROUTES ---

@app.route('/upload_photo', methods=['POST'])
@login_required
def upload_photo():
    if 'photo' not in request.files:
        flash("No file part", "error")
        return redirect(request.referrer)
    
    file = request.files['photo']
    if file.filename == '':
        flash("No selected file", "error")
        return redirect(request.referrer)

    if file:
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = secure_filename(f"user{current_user.id}_{int(datetime.now().timestamp())}.{ext}")
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        current_user.profile_pic = filename
        db.session.commit()
        flash("Vault profile updated!", "success")
    return redirect(request.referrer)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user:
            flash("Guardian ID already taken!", "error")
            return redirect(url_for('register'))
        
        hashed_pw = generate_password_hash(request.form['password'], method='pbkdf2:sha256')
        new_user = User(username=request.form['username'], password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! Decrypt your vault.", "success")
        return redirect(url_for('login'))
    return render_template('auth.html', mode='register')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
        flash("Invalid passkey or ID.", "error")
    return render_template('auth.html', mode='login')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    now = datetime.now(timezone.utc)
    todays = Capsule.query.filter(db.func.date(Capsule.unlock_date) == now.date(), Capsule.user_id == current_user.id).all()
    pending = Capsule.query.filter(Capsule.unlock_date > now, Capsule.user_id == current_user.id).order_by(Capsule.unlock_date.asc()).all()
    history_all = Capsule.query.filter(Capsule.unlock_date <= now, Capsule.user_id == current_user.id).order_by(Capsule.unlock_date.desc()).all()
    return render_template('index.html', capsules=pending, todays_capsules=todays, history_capsules=history_all, active_page='home')

@app.route('/history')
@login_required
def history():
    unlocked = Capsule.query.filter(Capsule.unlock_date <= datetime.now(timezone.utc), Capsule.user_id == current_user.id).order_by(Capsule.unlock_date.desc()).all()
    return render_template('index.html', capsules=unlocked, active_page='history')

@app.route('/diary', methods=['GET', 'POST'])
@login_required
def diary():
    if request.method == 'POST':
        content = request.form.get('content')
        if content:
            new_entry = DiaryEntry(content=content, user_id=current_user.id)
            db.session.add(new_entry)
            db.session.commit()
        return redirect(url_for('diary'))
    entries = DiaryEntry.query.filter_by(user_id=current_user.id).order_by(DiaryEntry.date_posted.desc()).all()
    return render_template('index.html', entries=entries, active_page='diary')

@app.route('/bury', methods=['POST'])
@login_required
def bury():
    try:
        unlock_date = datetime.strptime(request.form.get('unlock_date'), '%Y-%m-%d')
        new_capsule = Capsule(message=request.form.get('message'), unlock_date=unlock_date, user_id=current_user.id)
        db.session.add(new_capsule)
        db.session.commit()
    except:
        flash("System error: Invalid transmission date.", "error")
    return redirect(url_for('index'))

@app.route('/delete/<int:id>')
@login_required
def delete(id):
    capsule = Capsule.query.get_or_404(id)
    if capsule.user_id == current_user.id:
        db.session.delete(capsule)
        db.session.commit()
    return redirect(request.referrer or url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')