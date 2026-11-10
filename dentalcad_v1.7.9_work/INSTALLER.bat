@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
title DentalCAD - installation sécurisée
color 0B

rem Lancez ce fichier depuis le dossier extrait dentalcad.
rem Il ne supprime jamais le dossier existant et ne remplace jamais .env.

 echo.
echo ============================================================
echo       DENTALCAD - INSTALLATION / MISE A JOUR SURE
echo ============================================================
echo.

where docker >nul 2>&1
if errorlevel 1 (
  echo ERREUR : Docker n'est pas trouve dans PATH.
  echo Installez Docker Desktop, ouvrez-le, puis relancez ce fichier.
  pause
  exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
  echo ERREUR : Docker Desktop n'est pas pret.
  echo Lancez Docker Desktop et attendez que son moteur soit demarre.
  pause
  exit /b 1
)

if not exist "docker-compose.yml" (
  echo ERREUR : docker-compose.yml absent.
  echo Extrayez l'archive complete, puis lancez ce fichier depuis le dossier dentalcad.
  pause
  exit /b 1
)
if not exist ".env" (
  if not exist ".env.example" (
    echo ERREUR : .env.example absent.
    pause
    exit /b 1
  )
  echo Le fichier .env est absent. Creation d'un modele a completer...
  copy /y ".env.example" ".env" >nul
  echo.
  echo IMPORTANT : ouvrez .env et renseignez les secrets avant de continuer.
  echo Aucun mot de passe par defaut ne sera cree par ce script.
  notepad ".env"
  echo.
  echo Quand .env est complet et enregistre, relancez INSTALLER_SÛR.bat.
  pause
  exit /b 2
)

rem Verifie les variables obligatoires sans afficher leurs valeurs.
findstr /R /C:"^POSTGRES_PASSWORD=..*" ".env" >nul || goto env_error
findstr /R /C:"^ORTHANC_PASSWORD=..*" ".env" >nul || goto env_error
findstr /R /C:"^JWT_SECRET_KEY=................................" ".env" >nul || goto env_error
findstr /R /C:"^ADMIN_EMAIL=..*" ".env" >nul || goto env_error
findstr /R /C:"^ADMIN_PASSWORD=............*" ".env" >nul || goto env_error

echo.
echo [1/4] Verification de la configuration Docker Compose...
docker compose config -q
if errorlevel 1 (
  echo ERREUR : configuration Compose invalide. Corrigez .env et reessayez.
  pause
  exit /b 1
)

rem Sauvegarde locale horodatee avant toute reconstruction.
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%I"
for %%I in ("%CD%") do set "PROJECT=%%~nxI"
set "BACKUP=%CD%_backup_%STAMP%"
echo.
echo [2/4] Sauvegarde du dossier du projet :
echo %BACKUP%
mkdir "%BACKUP%" 2>nul
if errorlevel 1 (
  echo ERREUR : impossible de creer le dossier de sauvegarde. Arret sans modification.
  pause
  exit /b 1
)
robocopy "%CD%" "%BACKUP%" /E /COPY:DAT /DCOPY:DAT /R:1 /W:1 /XD ".git" "__pycache__" ".pytest_cache" >nul
set "RC=%ERRORLEVEL%"
if %RC% GEQ 8 (
  echo ERREUR : la sauvegarde a echoue. Aucune reconstruction lancee.
  echo Verifiez le dossier : %BACKUP%
  pause
  exit /b 1
)
echo Sauvegarde du dossier terminee. Les volumes Docker ne sont pas inclus dans cette copie.
echo Pour les donnees de la base, utilisez aussi votre procedure de sauvegarde PostgreSQL.

echo.
echo [3/4] Construction et demarrage des services...
docker compose up -d --build
if errorlevel 1 (
  echo ERREUR : Docker Compose a echoue. Consultez les journaux avec : docker compose logs --tail=100
  pause
  exit /b 1
)

echo.
echo [4/4] Verification de l'API...
set /a COUNT=0
:health_wait
set /a COUNT+=1
curl.exe --fail --silent --show-error http://127.0.0.1:8010/health >nul 2>&1
if not errorlevel 1 goto ready
if %COUNT% GEQ 40 goto health_failed
timeout /t 3 /nobreak >nul
goto health_wait

:ready
echo.
echo DentalCAD repond sur http://127.0.0.1:5173
echo API : http://127.0.0.1:8010/health
echo Sauvegarde du projet : %BACKUP%
echo.
echo Rappel : verification technique seulement, pas une validation clinique.
start "" "http://127.0.0.1:5173"
pause
exit /b 0

:env_error
echo ERREUR : une variable obligatoire de .env est vide ou trop courte.
echo Verifiez POSTGRES_PASSWORD, ORTHANC_PASSWORD, JWT_SECRET_KEY,
echo ADMIN_EMAIL et ADMIN_PASSWORD. Ne partagez jamais votre fichier .env.
pause
exit /b 1

:health_failed
echo ERREUR : l'API n'a pas repondu dans le delai imparti.
echo Diagnostic : docker compose ps
 echo             docker compose logs --tail=100 backend
pause
exit /b 1
