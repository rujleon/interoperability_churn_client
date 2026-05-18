"""
Customer Churn Prediction Model
Trains a Random Forest classifier on synthetic telecom data
"""

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

np.random.seed(42)


def generate_synthetic_data(n=5000):
    """Generate realistic telecom churn dataset"""
    data = {
        "tenure_months": np.random.randint(1, 72, n),
        "monthly_charges": np.random.uniform(20, 120, n),
        "total_charges": np.random.uniform(50, 8000, n),
        "num_products": np.random.randint(1, 6, n),
        "has_internet": np.random.choice([0, 1], n, p=[0.3, 0.7]),
        "has_phone": np.random.choice([0, 1], n, p=[0.1, 0.9]),
        "contract_type": np.random.choice(
            [0, 1, 2], n
        ),  # 0=month-to-month, 1=one year, 2=two year
        "payment_method": np.random.choice([0, 1, 2, 3], n),
        "paperless_billing": np.random.choice([0, 1], n),
        "tech_support": np.random.choice([0, 1], n, p=[0.4, 0.6]),
        "online_security": np.random.choice([0, 1], n, p=[0.45, 0.55]),
        "num_support_tickets": np.random.randint(0, 10, n),
        "avg_monthly_long_distance": np.random.uniform(0, 50, n),
        "days_since_last_interaction": np.random.randint(0, 365, n),
    }

    df = pd.DataFrame(data)

    # Realistic churn probability based on features
    churn_score = (
        (df["contract_type"] == 0) * 0.35
        + (df["tenure_months"] < 12) * 0.25
        + (df["monthly_charges"] > 80) * 0.15
        + (df["num_support_tickets"] > 4) * 0.20
        + (df["tech_support"] == 0) * 0.10
        + (df["online_security"] == 0) * 0.08
        + (df["days_since_last_interaction"] > 200) * 0.12
        - (df["num_products"] > 3) * 0.10
        - (df["tenure_months"] > 36) * 0.15
        + np.random.normal(0, 0.1, n)
    )
    df["churn"] = (churn_score > 0.5).astype(int)
    return df


def train():
    print("📊 Generating training data...")
    df = generate_synthetic_data(5000)

    feature_cols = [
        "tenure_months",
        "monthly_charges",
        "total_charges",
        "num_products",
        "has_internet",
        "has_phone",
        "contract_type",
        "payment_method",
        "paperless_billing",
        "tech_support",
        "online_security",
        "num_support_tickets",
        "avg_monthly_long_distance",
        "days_since_last_interaction",
    ]

    X = df[feature_cols]
    y = df["churn"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    print("🤖 Training Gradient Boosting model...")
    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "model",
                GradientBoostingClassifier(
                    n_estimators=200, learning_rate=0.05, max_depth=4, random_state=42
                ),
            ),
        ]
    )

    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]

    print("\n📈 Model Performance:")
    print(classification_report(y_test, y_pred))
    print(f"ROC-AUC Score: {roc_auc_score(y_test, y_proba):.4f}")

    import pathlib

    BASE_DIR = pathlib.Path(__file__).resolve().parent
    BASE_DIR.mkdir(exist_ok=True)
    joblib.dump(pipeline, str(BASE_DIR / "churn_model.pkl"))
    joblib.dump(feature_cols, str(BASE_DIR / "feature_cols.pkl"))
    print(f"\n✅ Model saved to {BASE_DIR / 'churn_model.pkl'}")
    return pipeline, feature_cols


if __name__ == "__main__":
    train()
