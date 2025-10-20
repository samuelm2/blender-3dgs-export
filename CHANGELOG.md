# Changelog

## Version 0.2.0 - UI Panel Update

### Major Changes

**Converted from File > Export menu to dedicated Properties panel**

The addon now features a dedicated panel in the Properties Editor under Scene Properties, providing a much more intuitive and accessible user experience with a prominent, dedicated workspace feel.

### New Features

- **Dedicated Properties Panel**: 
  - Located in Properties Editor > Scene Properties
  - Appears alongside other scene settings like Scene, Render, Output properties
  - All export controls in one prominent location

- **Live Camera Counter**: 
  - Shows number of cameras in scene in real-time
  - Disables export button when no cameras present

- **Enhanced Settings**:
  - Output Directory picker with file browser
  - Format selector (Text/Binary)
  - Optional image rendering toggle

- **Better User Feedback**:
  - Progress bar during export
  - Success/error notifications
  - Built-in quick guide in the panel

- **Smart Validation**:
  - Checks for cameras before export
  - Validates output path
  - Clear error messages

### Technical Changes

- **Property Group**: Settings now stored in `scene.colmap_export_settings`
- **Refactored Export**: Core export function separated from UI operators
- **Updated Metadata**: 
  - Category changed to "Scene" (was "Import-Export")
  - Location updated to Properties Editor > Scene Properties
  - Version bumped to 0.2.0

### Migration Notes

If you were using the old File > Export menu:
- The functionality is identical, just accessed differently
- Settings are now persistent per-scene
- Default output path is now relative to the blend file (`//colmap_export`)

### Breaking Changes

- File > Export menu items removed
- Old operator IDs changed from `object.colmap_dataset_generator_*` to `colmap.export`

---

## Version 0.1.0 - Initial Release

- Basic COLMAP export functionality
- File > Export menu integration
- Text and Binary format support

