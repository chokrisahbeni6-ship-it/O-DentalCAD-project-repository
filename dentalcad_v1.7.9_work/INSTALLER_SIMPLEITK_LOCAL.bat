@echo off
setlocal EnableExtensions
chcp 65001 >nul
title DentalCAD - Installation locale de SimpleITK
color 0B

echo.
echo ============================================================
echo   DENTALCAD - INSTALLATION LOCALE DE SIMPLEITK
echo ============================================================
echo.
echo Ce script installe SimpleITK dans Python sur cet ordinateur.
echo Il ne modifie pas les fichiers du projet ni la base de donnees.
echo Pour le backend Docker, SimpleITK est installe lors de la
 echo construction de l'image a partir de backend\requirements.txt.
echo.

set "PYEXE="
where py >nul 2>&1
if not errorlevel 1 set "PYEXE=py -3"
if not defined PYEXE (
  where python >nul 2>&1
  if not errorlevel 1 set "PYEXE=python"
)
if not defined PYEXE (
  echo ERREUR : Python 3 est introuvable.
  echo Installez Python 3 depuis https://www.python.org/downloads/windows/
  echo Cochez l'option d'ajout de Python au PATH, puis relancez ce script.
  pause
  exit /b 1
)

echo [1/3] Verification de Python...
%PYEXE% --version
if errorlevel 1 goto erreur

echo.
echo [2/3] Installation de SimpleITK 2.3.1...
%PYEXE% -m pip install SimpleITK==2.3.1
if errorlevel 1 goto erreur

echo.
echo [3/3] Verification de l'installation...
%PYEXE% -c "import SimpleITK as sitk; print(sitk.Version())"
if errorlevel 1 goto erreur

echo.
echo SUCCES : SimpleITK est installe et importable dans cet environnement Python.
echo Si le telechargement echoue, verifiez la connexion Internet ou le proxy.
echo Pour tester l'export STL de production, lancez ensuite :
echo python research\validation\benchmark_mesh_production.py
echo.
pause
exit /b 0

:erreur
echo.
echo ECHEC : l'installation ou la verification a echoue.
echo Verifiez la connexion Internet, la version de Python et les messages ci-dessus.
echo Aucun fichier du projet ni aucune base de donnees n'a ete supprime.
pause
exit /b 1
