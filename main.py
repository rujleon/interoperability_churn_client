from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import joblib
import numpy as np

# ====================== APP INIT ======================
app = Flask(__name__)

# --- Config depuis variables d'environnement (Docker) ---
app.secret_key = os.environ.get("SECRET_KEY", "changez_moi_en_prod_2026")

DB_USER = os.environ.get("POSTGRES_USER", "admin")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "admin123")
DB_HOST = os.environ.get("POSTGRES_HOST", "postgres_db")  # nom du service Docker
DB_PORT = os.environ.get("POSTGRES_PORT", "5432")
DB_NAME = os.environ.get("POSTGRES_DB", "churn_db")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ====================== FLASK-LOGIN ======================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
login_manager.login_message_category = "info"


# ====================== MODÈLES DB ======================
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    fullname = db.Column(db.String(150), nullable=True)
    password = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(50), nullable=False, default="recruiter")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password, raw_password)


class ChurnPrediction(db.Model):
    """Historique des prédictions de churn."""

    __tablename__ = "churn_predictions"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.String(100), nullable=False)
    predicted_at = db.Column(db.DateTime, default=datetime.utcnow)
    churn_prob = db.Column(db.Float, nullable=False)  # probabilité 0-1
    churn_label = db.Column(db.Boolean, nullable=False)  # True = churn
    features_used = db.Column(db.Text, nullable=True)  # JSON des features
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))

    user = db.relationship("User", backref="predictions")


# ====================== USER LOADER ======================
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ====================== CHARGEMENT MODÈLE ML ======================
MODEL_PATH = os.path.join("models", "XGBClassifier_churn26.pkl")


def load_model():
    """Charge le modèle pickle s'il existe."""
    if os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, "rb") as f:
            return joblib.load(f)
    return None


model = load_model()


# ====================== SEED DB ======================
def seed_default_users():
    """Crée les utilisateurs par défaut si la DB est vide."""
    if User.query.count() == 0:
        defaults = [
            {
                "username": "admin",
                "password": "admin2025",
                "role": "admin",
                "email": "admin@predict.hr",
                "fullname": "Administrateur",
            },
            {
                "username": "rh_manager",
                "password": "rh2024",
                "role": "manager",
                "email": "manager@predict.hr",
                "fullname": "RH Manager",
            },
            {
                "username": "recruiter",
                "password": "recruit2024",
                "role": "recruiter",
                "email": "recruiter@predict.hr",
                "fullname": "Recruiter",
            },
        ]
        for d in defaults:
            u = User(
                username=d["username"],
                email=d["email"],
                fullname=d["fullname"],
                role=d["role"],
            )
            u.set_password(d["password"])
            db.session.add(u)
        db.session.commit()
        print("✅ Utilisateurs par défaut créés.")


# ====================== ROUTES AUTH ======================
@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash(f"Bienvenue {user.fullname or username} !", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard"))
        else:
            flash("Nom d'utilisateur ou mot de passe incorrect.", "danger")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Déconnexion réussie.", "info")
    return redirect(url_for("index"))


# ====================== DASHBOARD ======================
@app.route("/dashboard")
@login_required
def dashboard():
    total_pred = ChurnPrediction.query.count()
    churn_count = ChurnPrediction.query.filter_by(churn_label=True).count()
    no_churn = total_pred - churn_count
    avg_prob = db.session.query(db.func.avg(ChurnPrediction.churn_prob)).scalar() or 0
    recent_preds = (
        ChurnPrediction.query.order_by(ChurnPrediction.predicted_at.desc())
        .limit(10)
        .all()
    )

    metrics = {
        "total_predictions": total_pred,
        "churn_count": churn_count,
        "no_churn_count": no_churn,
        "avg_churn_prob": round(float(avg_prob) * 100, 1),
        "churn_rate": round(churn_count / total_pred * 100, 1) if total_pred else 0,
    }
    return render_template(
        "dashboard.html", metrics=metrics, recent_preds=recent_preds, user=current_user
    )


# ====================== PRÉDICTION ======================
@app.route("/predict", methods=["GET", "POST"])
@login_required
def predict():
    result = None

    if request.method == "POST":
        if model is None:
            flash(
                "Modèle ML non chargé. Placez churn_model.pkl dans /models.", "danger"
            )
            return render_template("predict.html", result=None)

        try:
            # --- Récupération des features depuis le formulaire ---
            features = [
                float(request.form.get("tenure", 0)),
                float(request.form.get("monthly_charges", 0)),
                float(request.form.get("total_charges", 0)),
                int(request.form.get("num_services", 0)),
                int(request.form.get("contract_type", 0)),  # 0=M2M, 1=1an, 2=2ans
                int(request.form.get("payment_method", 0)),
                int(request.form.get("paperless_billing", 0)),
                int(request.form.get("tech_support", 0)),
            ]
            X = np.array(features).reshape(1, -1)

            prob = float(model.predict_proba(X)[0][1])
            churn_label = prob >= 0.5
            customer_id = request.form.get("customer_id", "N/A").strip()

            # --- Sauvegarde en DB ---
            pred = ChurnPrediction(
                customer_id=customer_id,
                churn_prob=prob,
                churn_label=churn_label,
                features_used=str(dict(request.form)),
                created_by=current_user.id,
            )
            db.session.add(pred)
            db.session.commit()

            result = {
                "customer_id": customer_id,
                "prob": round(prob * 100, 2),
                "label": "Churn probable" if churn_label else "Client fidèle",
                "risk_class": (
                    "danger" if prob >= 0.7 else "warning" if prob >= 0.4 else "success"
                ),
            }
            flash(f"Prédiction enregistrée pour {customer_id}.", "success")

        except Exception as e:
            flash(f"Erreur lors de la prédiction : {e}", "danger")

    return render_template("predict.html", result=result, user=current_user)


# ====================== HISTORIQUE ======================
@app.route("/history")
@login_required
def history():
    page = request.args.get("page", 1, type=int)
    preds = ChurnPrediction.query.order_by(
        ChurnPrediction.predicted_at.desc()
    ).paginate(page=page, per_page=20)
    return render_template("history.html", preds=preds, user=current_user)


# ====================== ADMIN ======================
@app.route("/admin/users")
@login_required
def list_users():
    if current_user.role != "admin":
        flash("Accès réservé aux administrateurs.", "danger")
        return redirect(url_for("dashboard"))
    users = User.query.all()
    return render_template("admin_users.html", users=users, user=current_user)


@app.route("/admin/users/add", methods=["GET", "POST"])
@login_required
def add_user():
    if current_user.role != "admin":
        flash("Accès refusé.", "danger")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "recruiter")
        email = request.form.get("email", "").strip()
        fullname = request.form.get("fullname", "").strip()

        if User.query.filter_by(username=username).first():
            flash("Nom d'utilisateur déjà utilisé.", "danger")
        else:
            u = User(username=username, email=email, fullname=fullname, role=role)
            u.set_password(password)
            db.session.add(u)
            db.session.commit()
            flash(f"Utilisateur {username} créé.", "success")
            return redirect(url_for("list_users"))

    return render_template("add_user.html", user=current_user)


# ====================== API JSON ======================
@app.route("/api/predict", methods=["POST"])
@login_required
def api_predict():
    """Endpoint JSON pour intégration externe."""
    if model is None:
        return jsonify({"error": "Modèle non chargé"}), 503

    data = request.get_json(force=True)
    try:
        features = np.array(data["features"]).reshape(1, -1)
        prob = float(model.predict_proba(features)[0][1])
        return jsonify(
            {
                "customer_id": data.get("customer_id", "N/A"),
                "churn_probability": round(prob, 4),
                "churn": prob >= 0.5,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ====================== CONTEXT / ERRORS ======================
@app.context_processor
def utility_processor():
    return dict(app_name="PredictHR Churn", app_version="2.0.0")


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500


# ====================== ENTRYPOINT ======================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Crée les tables si elles n'existent pas
        seed_default_users()  # Seed utilisateurs par défaut
    app.run(
        debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true",
        host="0.0.0.0",
        port=5000,
    )
