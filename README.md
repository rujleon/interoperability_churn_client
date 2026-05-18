---
title: ChurnGuard - Customer Churn Prediction API
emoji: 🔮
colorFrom: blue
colorTo: purple
sdk: docker
sdk_version: "3.11"
app_file: Dockerfile
pinned: false
license: mit
---

# 🔮 ChurnGuard — Customer Churn Prediction API

Une API de prédiction de churn client complète, sécurisée et prête pour la production.

## 🏗️ Architecture

churn-app/
├── app/
│ ├── main.py # FastAPI routes et configuration
│ ├── database.py # Modèles SQLAlchemy + SQLite/PostgreSQL
│ ├── security.py # Authentification par token HMAC-SHA256
│ ├── predictor.py # Service de prédiction ML (singleton)
│ └── schemas.py # Schémas Pydantic
├── ml/
│ └── train_model.py # Entraînement du modèle (Gradient Boosting)
├── templates/
│ └── index.html # Dashboard web interactif
├── Dockerfile # Build multi-stage optimisé
└── requirements.txt


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

## 🚀 Déploiement sur Hugging Face Spaces

Ce Space utilise **Docker** pour déployer l'API automatiquement.

### Accès à l'API

Une fois le build terminé, l'API est disponible à l'adresse :

https://NARINDRANJANAHARY-churn-client-prediction.hf.space



### Documentation Swagger

https://NARINDRANJANAHARY-churn-client-prediction.hf.space/docs

