@echo off
echo ============================================
echo     ChurnGuard - Lancement sur Windows
echo ============================================
echo.

:: Verifier Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERREUR] Python n'est pas installe !
    echo Telechargez-le sur https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] Creation de l'environnement virtuel...
IF NOT EXIST venv (
    python -m venv venv
)

echo [2/4] Activation et installation des dependances...
call venv\Scripts\activate


echo [3/4] Entrainement du modele ML...
IF NOT EXIST ml\churn_model.pkl (
    python ml\train_model.py
) ELSE (
    echo      Modele deja entraine, on passe...
)

echo [4/4] Lancement de l'API...
echo.
echo ============================================
echo  API disponible sur : http://localhost:8000
echo  Dashboard          : http://localhost:8000
echo  Documentation      : http://localhost:8000/docs
echo  Appuyez sur Ctrl+C pour arreter
echo ============================================
echo.

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause
