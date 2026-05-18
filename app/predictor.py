"""
ML Prediction Service: Loads model and makes predictions
"""

import os
import pathlib
from typing import List, Tuple

import joblib
import numpy as np

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
MODEL_PATH = os.getenv("MODEL_PATH", str(BASE_DIR / "ml" / "churn_model.pkl"))
FEATURES_PATH = os.getenv("FEATURES_PATH", str(BASE_DIR / "ml" / "feature_cols.pkl"))


class ChurnPredictor:
    _instance = None
    _model = None
    _feature_cols = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self):
        """Load model from disk (singleton pattern)"""
        if self._model is None:
            if not os.path.exists(MODEL_PATH):
                raise FileNotFoundError(
                    f"Model not found at {MODEL_PATH}. Run train_model.py first."
                )
            self._model = joblib.load(MODEL_PATH)
            self._feature_cols = joblib.load(FEATURES_PATH)
            print(f"✅ Model loaded from {MODEL_PATH}")

    @property
    def is_loaded(self):
        return self._model is not None

    def predict(self, features: dict) -> Tuple[float, bool, str, str, str, List[str]]:
        """
        Returns: (probability, prediction, risk_level, risk_color, recommendation, key_factors)
        """
        if not self.is_loaded:
            self.load()

        X = np.array([[features[col] for col in self._feature_cols]])
        prob = self._model.predict_proba(X)[0][1]
        prediction = bool(prob >= 0.5)

        # Risk level classification
        if prob < 0.3:
            risk_level = "Faible"
            risk_color = "#10b981"
            recommendation = "Client fidèle. Proposez des offres de fidélisation pour renforcer la relation."
        elif prob < 0.5:
            risk_level = "Modéré"
            risk_color = "#f59e0b"
            recommendation = "Risque modéré. Surveillez l'engagement et proposez un contact personnalisé."
        elif prob < 0.75:
            risk_level = "Élevé"
            risk_color = "#ef4444"
            recommendation = "Risque élevé de churn. Action immédiate recommandée : offre de rétention ou appel commercial."
        else:
            risk_level = "Critique"
            risk_color = "#7f1d1d"
            recommendation = "⚠️ Churn quasi-certain. Intervention urgente : réduction tarifaire ou upgrade offert."

        # Key factors analysis
        key_factors = self._analyze_key_factors(features, prob)

        return prob, prediction, risk_level, risk_color, recommendation, key_factors

    def _analyze_key_factors(self, features: dict, prob: float) -> List[str]:
        """Identify the top risk/protective factors"""
        factors = []

        if features["contract_type"] == 0:
            factors.append("⚠️ Contrat mois-à-mois (très volatile)")
        elif features["contract_type"] == 2:
            factors.append("✅ Contrat 2 ans (engagement fort)")

        if features["tenure_months"] < 12:
            factors.append(f"⚠️ Client récent ({features['tenure_months']} mois)")
        elif features["tenure_months"] > 36:
            factors.append(f"✅ Client fidèle ({features['tenure_months']} mois)")

        if features["num_support_tickets"] > 4:
            factors.append(
                f"⚠️ Nombreux tickets support ({features['num_support_tickets']})"
            )

        if features["monthly_charges"] > 80:
            factors.append(
                f"⚠️ Charges élevées ({features['monthly_charges']:.0f}$/mois)"
            )

        if not features["tech_support"]:
            factors.append("⚠️ Sans support technique")
        else:
            factors.append("✅ Support technique actif")

        if not features["online_security"]:
            factors.append("⚠️ Sans sécurité en ligne")

        if features["num_products"] >= 3:
            factors.append(f"✅ Multi-produits ({features['num_products']} services)")

        if features["days_since_last_interaction"] > 180:
            factors.append(
                f"⚠️ Inactif depuis {features['days_since_last_interaction']} jours"
            )

        return factors[:5]  # Top 5 factors


# Singleton instance
predictor = ChurnPredictor()
