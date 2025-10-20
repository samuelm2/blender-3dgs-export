#!/bin/bash

VERSION=${1:-develop}

# Create dist folder and zip
mkdir -p dist
zip -r dist/blender-exporter-colmap_$VERSION.zip blender-exporter-colmap -x "*.pyc" -x "*__pycache__*"

# Install to Blender addons directory (optional - uncomment to enable)
# Adjust the Blender version number as needed
BLENDER_VERSION="4.4"  # Change this to your Blender version (e.g., 3.6, 4.0, 4.1, etc.)
BLENDER_ADDONS="$APPDATA/Blender Foundation/Blender/$BLENDER_VERSION/scripts/addons"

if [ -d "$BLENDER_ADDONS" ]; then
    echo "Installing to Blender addons folder: $BLENDER_ADDONS"
    rm -rf "$BLENDER_ADDONS/blender-exporter-colmap"
    cp -r blender-exporter-colmap "$BLENDER_ADDONS/"
    echo "✓ Addon installed! Reload scripts in Blender (Ctrl+Alt+R)"
else
    echo "⚠ Blender addons folder not found at: $BLENDER_ADDONS"
    echo "Please adjust BLENDER_VERSION in the script"
fi
