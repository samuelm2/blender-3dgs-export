@echo off
:: Quick install script for Blender addon
:: Adjust the version number below to match your Blender installation

SET BLENDER_VERSION=4.4
SET ADDON_DIR=%APPDATA%\Blender Foundation\Blender\%BLENDER_VERSION%\scripts\addons
SET ADDON_NAME=blender-exporter-colmap

echo ========================================
echo  COLMAP Exporter - Quick Install
echo ========================================
echo.

:: Check if Blender addons directory exists
if not exist "%ADDON_DIR%" (
    echo [ERROR] Blender %BLENDER_VERSION% addons folder not found!
    echo Expected location: %ADDON_DIR%
    echo.
    echo Please edit this file and change BLENDER_VERSION to match your installation
    echo Common versions: 3.6, 4.0, 4.1, 4.2, etc.
    pause
    exit /b 1
)

echo Installing to: %ADDON_DIR%
echo.

:: Remove old version
if exist "%ADDON_DIR%\%ADDON_NAME%" (
    echo Removing old version...
    rmdir /s /q "%ADDON_DIR%\%ADDON_NAME%"
)

:: Copy new version
echo Copying addon files...
xcopy /E /I /Y "%ADDON_NAME%" "%ADDON_DIR%\%ADDON_NAME%"

echo.
echo ========================================
echo  SUCCESS! Addon installed.
echo ========================================
echo.
echo Next steps:
echo   1. Open Blender
echo   2. Press F3 and search "Reload Scripts"
echo   3. Or restart Blender
echo   4. Find the addon in Output Properties
echo.
pause

