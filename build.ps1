# PowerShell build script for Windows
param(
    [string]$Version = "develop",
    [string]$BlenderVersion = "4.0"  # Change to your Blender version
)

Write-Host "Building COLMAP Exporter v$Version" -ForegroundColor Cyan

# Create dist folder and zip
New-Item -ItemType Directory -Force -Path "dist" | Out-Null
$zipPath = "dist\blender-exporter-colmap_$Version.zip"

Write-Host "Creating ZIP: $zipPath" -ForegroundColor Yellow
Compress-Archive -Path "blender-exporter-colmap\*" -DestinationPath $zipPath -Force

# Install to Blender addons directory
$blenderAddons = "$env:APPDATA\Blender Foundation\Blender\$BlenderVersion\scripts\addons"
$addonTarget = "$blenderAddons\blender-exporter-colmap"

if (Test-Path $blenderAddons) {
    Write-Host "`nInstalling to Blender addons folder..." -ForegroundColor Yellow
    Write-Host "  Location: $blenderAddons" -ForegroundColor Gray
    
    # Remove old version if exists
    if (Test-Path $addonTarget) {
        Remove-Item -Path $addonTarget -Recurse -Force
        Write-Host "  - Removed old version" -ForegroundColor Gray
    }
    
    # Copy new version
    Copy-Item -Path "blender-exporter-colmap" -Destination $addonTarget -Recurse -Force
    Write-Host "  ✓ Addon installed successfully!" -ForegroundColor Green
    Write-Host "`nNext steps:" -ForegroundColor Cyan
    Write-Host "  1. Open Blender" -ForegroundColor White
    Write-Host "  2. Press F3 and search 'Reload Scripts'" -ForegroundColor White
    Write-Host "  3. Or toggle the addon in Preferences > Add-ons" -ForegroundColor White
} else {
    Write-Host "`n⚠ Blender addons folder not found!" -ForegroundColor Red
    Write-Host "  Expected: $blenderAddons" -ForegroundColor Gray
    Write-Host "  Please adjust BlenderVersion parameter" -ForegroundColor Yellow
    Write-Host "  Example: .\build.ps1 -BlenderVersion '3.6'" -ForegroundColor Gray
}

Write-Host "`nDone!" -ForegroundColor Green

