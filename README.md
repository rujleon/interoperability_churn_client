# 🔮 ChurnGuard — Customer Churn Prediction API

Une API de prédiction de churn client complète, sécurisée et prête pour la production.

## 🏗️ Architecture

```
churn-app/
├── app/
│   ├── main.py          # FastAPI routes et configuration
│   ├── database.py      # Modèles SQLAlchemy + SQLite/PostgreSQL
│   ├── security.py      # Authentification par token HMAC-SHA256
│   ├── predictor.py     # Service de prédiction ML (singleton)
│   └── schemas.py       # Schémas Pydantic
├── ml/
│   └── train_model.py   # Entraînement du modèle (Gradient Boosting)
├── templates/
│   └── index.html       # Dashboard web interactif
├── Dockerfile           # Build multi-stage optimisé
├── docker-compose.yml   # Orchestration + Traefik SSL
└── requirements.txt
```

## 🤖 Modèle ML

- **Algorithme** : Gradient Boosting Classifier (scikit-learn)
- **Features** : 14 variables clients (ancienneté, contrat, charges, support, etc.)
- **Performance** : ROC-AUC > 0.88 sur données de test
- **Entraînement** : Automatique au build Docker (5 000 exemples synthétiques)

## 🔐 Sécurité

| Fonctionnalité | Détail |
|---|---|
| **Authentification** | Token HMAC-SHA256 par client (`churn_xxxx`) |
| **Validation** | Signature cryptographique à chaque requête |
| **Expiration** | Configurable (1–730 jours) |
| **Rate limiting** | 100 req/heure par client (configurable) |
| **Isolation** | Chaque client voit uniquement ses données |
| **Non-root** | Conteneur exécuté en tant qu'utilisateur non-root |

## 🚀 Déploiement

### Développement local

```bash
# 1. Cloner et configurer
cp .env.example .env
# Éditer .env avec vos valeurs

# 2. Lancer
docker compose up --build

# L'API est disponible sur http://localhost:8000
# Documentation Swagger : http://localhost:8000/docs
```

### Production (avec SSL automatique)

```bash
# Pré-requis : domaine DNS pointant vers votre serveur

# Configurer
export DOMAIN=api.mondomaine.com
export ACME_EMAIL=admin@mondomaine.com
export SECRET_KEY=$(openssl rand -hex 32)

# Lancer avec Traefik + Let's Encrypt
docker compose --profile production up -d

# L'API est disponible sur https://api.mondomaine.com
```

### Déploiement cloud (Railway, Render, Fly.io)

```bash
# Exemple Railway
railway login
railway new
railway up

# Exemple Render : connectez votre repo GitHub
# Build Command : docker build -t churnguard .
# Start Command : (défini dans Dockerfile)
```

## 📡 Utilisation de l'API

### 1. Créer un compte

```bash
curl -X POST http://localhost:8000/clients/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice Martin","email":"alice@co.com","company":"Acme"}'
```

Réponse :
```json
{
  "client_id": "cli_abc123def456",
  "api_token": "churn_8fa3b2c1d0e...",
  "token_expires_at": "2026-05-12T00:00:00"
}
```

### 2. Prédire le churn

```bash
curl -X POST http://localhost:8000/predict \
  -H "X-API-Token: churn_votre_token" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Jean Dupont",
    "tenure_months": 8,
    "monthly_charges": 89.5,
    "total_charges": 716.0,
    "num_products": 2,
    "has_internet": true,
    "has_phone": true,
    "contract_type": 0,
    "payment_method": 0,
    "paperless_billing": true,
    "tech_support": false,
    "online_security": false,
    "num_support_tickets": 5,
    "avg_monthly_long_distance": 12.5,
    "days_since_last_interaction": 45
  }'
```

Réponse :
```json
{
  "churn_probability": 0.7842,
  "churn_prediction": true,
  "risk_level": "Élevé",
  "risk_color": "#ef4444",
  "recommendation": "Risque élevé de churn. Action immédiate recommandée...",
  "key_factors": [
    "⚠️ Contrat mois-à-mois (très volatile)",
    "⚠️ Client récent (8 mois)",
    "⚠️ Nombreux tickets support (5)"
  ]
}
```

### 3. Prédiction en batch (jusqu'à 50 clients)

```bash
curl -X POST http://localhost:8000/predict/batch \
  -H "X-API-Token: churn_votre_token" \
  -H "Content-Type: application/json" \
  -d '{"customers": [{...}, {...}]}'
```

### 4. Voir vos statistiques

```bash
curl http://localhost:8000/predictions/stats \
  -H "X-API-Token: churn_votre_token"
```

## 📊 Endpoints

| Méthode | Endpoint | Description |
|---|---|---|
| POST | `/clients/register` | Créer un compte + recevoir un token |
| GET | `/clients/me` | Voir son profil |
| POST | `/clients/me/refresh-token` | Renouveler son token |
| POST | `/predict` | Prédiction individuelle |
| POST | `/predict/batch` | Prédictions en lot (≤50) |
| GET | `/predictions/history` | Historique des prédictions |
| GET | `/predictions/stats` | Statistiques agrégées |
| GET | `/health` | Statut de l'API |
| GET | `/docs` | Documentation Swagger |

## 🌡️ Variables d'entrée

| Variable | Type | Description |
|---|---|---|
| `tenure_months` | int (0-240) | Ancienneté en mois |
| `monthly_charges` | float | Charges mensuelles ($) |
| `total_charges` | float | Charges totales ($) |
| `num_products` | int (1-10) | Nombre de produits |
| `contract_type` | int (0-2) | 0=mois/mois, 1=1an, 2=2ans |
| `payment_method` | int (0-3) | Mode de paiement |
| `has_internet` | bool | Service internet |
| `has_phone` | bool | Service téléphone |
| `tech_support` | bool | Support technique |
| `online_security` | bool | Sécurité en ligne |
| `paperless_billing` | bool | Facturation dématérialisée |
| `num_support_tickets` | int | Tickets support ouverts |
| `avg_monthly_long_distance` | float | Longue distance mensuelle ($) |
| `days_since_last_interaction` | int | Jours sans interaction |

## 🔄 Variables d'environnement

| Variable | Défaut | Description |
|---|---|---|
| `SECRET_KEY` | (requis) | Clé HMAC pour tokens |
| `DATABASE_URL` | SQLite | URL de base de données |
| `RATE_LIMIT_REQUESTS` | 100 | Requêtes max par heure |
| `WORKERS` | 2 | Workers Gunicorn |
| `DOMAIN` | localhost | Domaine pour SSL |
