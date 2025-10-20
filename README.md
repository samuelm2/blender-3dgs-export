# blender-exporter-colmap

Blender addon which generates a dataset for COLMAP by exporting Blender camera poses and rendering scene images. Features a dedicated UI panel for easy access and configuration.

## Features

- 🎨 **Dedicated Properties Panel** - Access all export settings from the Output Properties panel
- 📷 **Camera Management** - Automatically detects and exports all cameras in your scene
- 🎯 **Multiple Formats** - Export as text (.txt) or binary (.bin) COLMAP formats
- 🖼️ **Optional Rendering** - Choose to render images or export camera data only
- ✅ **User-Friendly** - Clear status messages and progress indicators

## Installation

1. Download this repository as a ZIP file (or use the pre-built release)
2. Open Blender
3. Go to `Edit` > `Preferences` > `Add-ons`
4. Click `Install...` and select the ZIP file
5. Enable the addon by checking the box next to "Render: COLMAP Exporter"

The COLMAP Export panel will now appear in the Properties Editor under Output Properties.

## How to use

You can generate a dataset for COLMAP in the following steps:

### 1. Place cameras in your scene

Add and position cameras in your scene as needed. The addon will automatically detect all camera objects.

![Place cameras on the scene](docs/images/00_how_to_use/01_place_cameras_in_scene.png)

### 2. Open the COLMAP Export panel

1. Open the **Properties Editor** (usually on the right side of Blender)
2. Click on the **Output Properties** icon (the printer icon 🖨️)
3. Scroll down to find the **"COLMAP Export"** panel
4. The panel shows the number of cameras in your scene

### 3. Configure export settings

- **Output Directory**: Choose where to save your COLMAP dataset
- **Format**: Select Text (.txt) or Binary (.bin) format
- **Render Images**: Toggle whether to render images from each camera

### 4. Export your dataset

Click the **"Export Dataset"** button. The addon will:
- Export camera intrinsic parameters to `cameras.txt/bin`
- Export camera poses to `images.txt/bin`  
- Render images to the `images/` folder (if enabled)
- Display a progress bar during export

### 5. Your COLMAP dataset is ready

You'll get a complete COLMAP dataset in your specified output directory: 

![Exported dataset](docs/images/00_how_to_use/03_exported_files.png)

There are also images rendered with parameters and from the view point of camera in `images` folder.

![Rendered cameras](docs/images/00_how_to_use/04_exported_images.png)

## output format

This script generate these files on a selected folder.

|Name|Description|
|:--|:--|
|📂images|Contains rendered images. Each image is rendered with  parameters (intrinsic and pose) of camera in the scene.|
|📄cameras.txt|Contains intrinsic paramters of each camera.|
|📄images.txt|Contains camera poses of each camera.|
|📄points3D.txt|Empty file|

For details, please refer to [COLMAP documentation](https://colmap.github.io/format.html).

## How to use in colmap

You can use COLMAP cli for executing SfM with generated dataset.

```cmd
colmap feature_extractor --database_path "/path/to/output/database.db" --image_path "/path/to/dataset/images"

colmap exhaustive_matcher --database_path "/path/to/output/database.db" 

colmap point_triangulator --database_path "/path/to/output/database.db" --image_path "/path/to/dataset/images" --input_path "/path/to/dataset" --output_path "/path/to/output/triangulated/sparse/model"
```

Then, the result of 3d reconstruction is placed `/path/to/output/triangulated/sparse/model".