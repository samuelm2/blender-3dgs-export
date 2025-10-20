import numpy as np
from pathlib import Path
import mathutils
from . ext.read_write_model import write_model, Camera, Image, Point3D
from bpy.props import StringProperty, EnumProperty, BoolProperty
import bpy
import os

bl_info = {
    "name": "COLMAP Exporter",
    "description": "Generates a dataset for COLMAP by exporting Blender camera poses and rendering scene.",
    "author": "Ohayoyogi",
    "version": (0, 2, 0),
    "blender": (3, 6, 0),
    "location": "Properties > Output Properties > COLMAP",
    "warning": "",
    "wiki_url": "https://github.com/ohayoyogi/blender-exporter-colmap",
    "tracker_url": "https://github.com/ohayoyogi/blender-exporter-colmap/issues",
    "category": "Render"
}


# Scene Properties
class ColmapExportSettings(bpy.types.PropertyGroup):
    output_path: StringProperty(
        name="Output Directory",
        description="Directory where COLMAP data will be exported",
        default="//colmap_export",
        subtype='DIR_PATH'
    )
    
    output_format: EnumProperty(
        name="Format",
        description="Output format for COLMAP model files",
        items=[
            ('TXT', "Text (.txt)", "Export as text files (human-readable)"),
            ('BIN', "Binary (.bin)", "Export as binary files (compact)")
        ],
        default='TXT'
    )
    
    render_images: BoolProperty(
        name="Render Images",
        description="Render images from each camera during export",
        default=True
    )
    
    export_points: BoolProperty(
        name="Export 3D Points",
        description="Export mesh vertices as 3D points (points3D file)",
        default=False
    )
    
    points_selected_only: BoolProperty(
        name="Selected Objects Only",
        description="Export 3D points only from selected mesh objects",
        default=False
    )


def extract_3d_points_from_scene(context, selected_only=False):
    """Extract 3D points from mesh objects in the scene"""
    points3D = {}
    point_id = 1
    
    # Get mesh objects based on selection mode
    if selected_only:
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
    else:
        mesh_objects = [obj for obj in context.scene.objects if obj.type == 'MESH']
    
    if not mesh_objects:
        return points3D
    
    for obj in mesh_objects:
        # Get the mesh data with modifiers applied
        depsgraph = context.evaluated_depsgraph_get()
        obj_eval = obj.evaluated_get(depsgraph)
        mesh = obj_eval.to_mesh()
        
        if mesh is None:
            continue
        
        # Get world matrix for transforming vertices
        world_matrix = obj.matrix_world
        
        # Get vertex colors if available
        has_vertex_colors = len(mesh.vertex_colors) > 0
        if has_vertex_colors:
            color_layer = mesh.vertex_colors.active
        
        # Get material color as fallback
        default_color = np.array([128, 128, 128], dtype=np.uint8)  # Gray
        if len(obj.material_slots) > 0 and obj.material_slots[0].material:
            mat = obj.material_slots[0].material
            if mat.use_nodes and mat.node_tree:
                # Try to get base color from Principled BSDF
                for node in mat.node_tree.nodes:
                    if node.type == 'BSDF_PRINCIPLED':
                        base_color = node.inputs['Base Color'].default_value
                        default_color = np.array([
                            int(base_color[0] * 255),
                            int(base_color[1] * 255),
                            int(base_color[2] * 255)
                        ], dtype=np.uint8)
                        break
        
        # Extract vertices
        for i, vert in enumerate(mesh.vertices):
            # Transform vertex to world space
            world_pos = world_matrix @ vert.co
            xyz = np.array([world_pos.x, world_pos.y, world_pos.z])
            
            # Get vertex color
            if has_vertex_colors:
                # Average color from all loops using this vertex
                loop_colors = []
                for loop in mesh.loops:
                    if loop.vertex_index == i:
                        color = color_layer.data[loop.index].color
                        loop_colors.append([
                            int(color[0] * 255),
                            int(color[1] * 255),
                            int(color[2] * 255)
                        ])
                if loop_colors:
                    rgb = np.array(loop_colors[0], dtype=np.uint8)
                else:
                    rgb = default_color
            else:
                rgb = default_color
            
            # Create Point3D entry
            points3D[point_id] = Point3D(
                id=point_id,
                xyz=xyz,
                rgb=rgb,
                error=0.0,  # No reconstruction error for ground truth
                image_ids=np.array([], dtype=int),  # No image correspondences
                point2D_idxs=np.array([], dtype=int)
            )
            point_id += 1
        
        # Clean up
        obj_eval.to_mesh_clear()
    
    return points3D


def export_colmap_dataset(context, dirpath: Path, format: str, render_images: bool = True):
    """Core export function that generates COLMAP dataset"""
    scene = context.scene
    scene_cameras = [i for i in scene.objects if i.type == "CAMERA"]
    
    if len(scene_cameras) == 0:
        return False, "No cameras found in scene"

    output_format = format if format in ['.txt', '.bin'] else '.txt'

    output_dir = dirpath
    images_dir = output_dir / 'images'

    output_dir.mkdir(parents=True, exist_ok=True)
    if render_images:
        images_dir.mkdir(parents=True, exist_ok=True)

    cameras = {}
    images = {}
    
    total_steps = len(scene_cameras)
    
    for idx, cam in enumerate(sorted(scene_cameras, key=lambda x: x.name_full + ".jpg")):
        camera_id = idx + 1
        filename = f'{cam.name_full}.jpg'
        width = scene.render.resolution_x
        height = scene.render.resolution_y
        focal_length = cam.data.lens
        sensor_width = cam.data.sensor_width
        sensor_height = cam.data.sensor_height
        fx = focal_length * width / sensor_width
        fy = focal_length * height / sensor_height
        
        # fx, fy, cx, cy, k1, k2, p1, p2
        params = [fx, fy, width/2, height/2, 0, 0, 0, 0]
        cameras[camera_id] = Camera(
            id=camera_id,
            model='OPENCV',
            width=width,
            height=height,
            params=params
        )

        image_id = camera_id
        rotation_mode_bk = cam.rotation_mode

        cam.rotation_mode = "QUATERNION"
        cam_rot_orig = mathutils.Quaternion(cam.rotation_quaternion)
        cam_rot = mathutils.Quaternion((
            cam_rot_orig.x,
            cam_rot_orig.w,
            cam_rot_orig.z,
            -cam_rot_orig.y))
        qw = cam_rot.w
        qx = cam_rot.x
        qy = cam_rot.y
        qz = cam_rot.z
        cam.rotation_mode = rotation_mode_bk

        T = mathutils.Vector(cam.location)
        T1 = -(cam_rot.to_matrix() @ T)

        tx = T1[0]
        ty = T1[1]
        tz = T1[2]
        images[image_id] = Image(
            id=image_id,
            qvec=np.array([qw, qx, qy, qz]),
            tvec=np.array([tx, ty, tz]),
            camera_id=camera_id,
            name=filename,
            xys=[],
            point3D_ids=[]
        )

        # Render scene if enabled
        if render_images:
            bpy.context.scene.camera = cam
            bpy.ops.render.render()
            bpy.data.images['Render Result'].save_render(
                str(images_dir / filename))
        
        yield 100.0 * (idx + 1) / (total_steps + 1)

    write_model(cameras, images, {}, str(output_dir), output_format)
    yield 100.0

    return True, f"Successfully exported {len(scene_cameras)} cameras"


# Global state for render callback
_export_state = {
    'is_rendering': False,
    'operator': None
}


# Operator with async rendering using handlers
class COLMAP_OT_export(bpy.types.Operator):
    bl_idname = "colmap.export"
    bl_label = "Export COLMAP Dataset"
    bl_description = "Export camera poses and render images for COLMAP"
    bl_options = {'REGISTER'}
    
    _timer = None
    _cameras = None
    _current_idx = 0
    _output_dir = None
    _images_dir = None
    _format = None
    _render_images = None
    _export_points = None
    _points_selected_only = None
    _cameras_data = {}
    _images_data = {}
    _points3D_data = {}
    _original_camera = None
    _is_rendering = False
    _render_complete_handler = None
    _render_cancel_handler = None
    
    def modal(self, context, event):
        if event.type == 'TIMER':
            # If currently rendering, wait for it to complete
            if self._is_rendering:
                return {'PASS_THROUGH'}
            
            # Check if we're done with all cameras
            if self._current_idx >= len(self._cameras):
                return self.finish(context)
            
            # Process next camera
            cam = self._cameras[self._current_idx]
            self.process_camera_data(context, cam, self._current_idx)
            
            # Start render if enabled
            if self._render_images:
                self.start_render(context, cam)
            else:
                # No rendering, move to next immediately
                self._current_idx += 1
                self.update_progress(context)
            
        return {'PASS_THROUGH'}
    
    def process_camera_data(self, context, cam, idx):
        """Export camera data (parameters and pose)"""
        scene = context.scene
        camera_id = idx + 1
        filename = f'{cam.name_full}.jpg'
        
        width = scene.render.resolution_x
        height = scene.render.resolution_y
        focal_length = cam.data.lens
        sensor_width = cam.data.sensor_width
        sensor_height = cam.data.sensor_height
        fx = focal_length * width / sensor_width
        fy = focal_length * height / sensor_height
        
        # Camera parameters
        params = [fx, fy, width/2, height/2, 0, 0, 0, 0]
        self._cameras_data[camera_id] = Camera(
            id=camera_id,
            model='OPENCV',
            width=width,
            height=height,
            params=params
        )
        
        # Camera pose
        rotation_mode_bk = cam.rotation_mode
        cam.rotation_mode = "QUATERNION"
        cam_rot_orig = mathutils.Quaternion(cam.rotation_quaternion)
        cam_rot = mathutils.Quaternion((
            cam_rot_orig.x,
            cam_rot_orig.w,
            cam_rot_orig.z,
            -cam_rot_orig.y))
        cam.rotation_mode = rotation_mode_bk
        
        T = mathutils.Vector(cam.location)
        T1 = -(cam_rot.to_matrix() @ T)
        
        self._images_data[camera_id] = Image(
            id=camera_id,
            qvec=np.array([cam_rot.w, cam_rot.x, cam_rot.y, cam_rot.z]),
            tvec=np.array([T1[0], T1[1], T1[2]]),
            camera_id=camera_id,
            name=filename,
            xys=[],
            point3D_ids=[]
        )
    
    def start_render(self, context, cam):
        """Start rendering for a camera"""
        context.scene.camera = cam
        self._is_rendering = True
        _export_state['is_rendering'] = True
        _export_state['operator'] = self
        
        self.update_progress(context)
        
        # Start render with INVOKE_DEFAULT to keep UI responsive
        bpy.ops.render.render('INVOKE_DEFAULT', write_still=False)
    
    def on_render_complete(self, scene, depsgraph=None):
        """Called when render completes"""
        if not _export_state['is_rendering'] or _export_state['operator'] != self:
            return
        
        # Save the rendered image
        cam = self._cameras[self._current_idx]
        filename = f'{cam.name_full}.jpg'
        bpy.data.images['Render Result'].save_render(
            str(self._images_dir / filename))
        
        # Move to next camera
        self._is_rendering = False
        _export_state['is_rendering'] = False
        self._current_idx += 1
    
    def on_render_cancel(self, scene, depsgraph=None):
        """Called if render is cancelled"""
        if not _export_state['is_rendering'] or _export_state['operator'] != self:
            return
        
        self._is_rendering = False
        _export_state['is_rendering'] = False
        # Don't increment, will retry or user can cancel operator
    
    def update_progress(self, context):
        """Update progress display"""
        progress = int(100 * (self._current_idx + 1) / len(self._cameras))
        status = f"COLMAP Export: "
        if self._is_rendering:
            status += f"Rendering camera {self._current_idx + 1}/{len(self._cameras)} ({progress}%)"
        else:
            status += f"Processing camera {self._current_idx + 1}/{len(self._cameras)} ({progress}%)"
        context.workspace.status_text_set(status)
    
    def finish(self, context):
        """Write model files and clean up"""
        # Remove handlers
        if self._render_complete_handler in bpy.app.handlers.render_complete:
            bpy.app.handlers.render_complete.remove(self._render_complete_handler)
        if self._render_cancel_handler in bpy.app.handlers.render_cancel:
            bpy.app.handlers.render_cancel.remove(self._render_cancel_handler)
        
        # Extract 3D points if enabled
        if self._export_points:
            self._points3D_data = extract_3d_points_from_scene(context, self._points_selected_only)
        
        # Write COLMAP model files
        write_model(
            self._cameras_data, 
            self._images_data, 
            self._points3D_data, 
            str(self._output_dir), 
            self._format
        )
        
        # Restore original camera
        if self._original_camera:
            context.scene.camera = self._original_camera
        
        # Clean up
        context.window_manager.event_timer_remove(self._timer)
        context.workspace.status_text_set(None)
        _export_state['is_rendering'] = False
        _export_state['operator'] = None
        
        self.report({'INFO'}, f"COLMAP dataset exported to: {self._output_dir}")
        return {'FINISHED'}

    def execute(self, context):
        settings = context.scene.colmap_export_settings
        
        # Resolve relative paths
        output_path = bpy.path.abspath(settings.output_path)
        self._output_dir = Path(output_path)
        
        if not output_path:
            self.report({'ERROR'}, "Please specify an output directory")
            return {'CANCELLED'}
        
        # Check for cameras
        scene_cameras = [i for i in context.scene.objects if i.type == "CAMERA"]
        if len(scene_cameras) == 0:
            self.report({'ERROR'}, "No cameras found in scene")
            return {'CANCELLED'}
        
        # Setup
        self._cameras = sorted(scene_cameras, key=lambda x: x.name_full)
        self._current_idx = 0
        self._format = '.txt' if settings.output_format == 'TXT' else '.bin'
        self._render_images = settings.render_images
        self._export_points = settings.export_points
        self._points_selected_only = settings.points_selected_only
        self._cameras_data = {}
        self._images_data = {}
        self._points3D_data = {}
        self._original_camera = context.scene.camera
        self._is_rendering = False
        
        # Create output directories
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._images_dir = self._output_dir / 'images'
        if self._render_images:
            self._images_dir.mkdir(parents=True, exist_ok=True)
        
        # Register render completion handlers
        self._render_complete_handler = self.on_render_complete
        self._render_cancel_handler = self.on_render_cancel
        bpy.app.handlers.render_complete.append(self._render_complete_handler)
        bpy.app.handlers.render_cancel.append(self._render_cancel_handler)
        
        # Start modal operator
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        
        return {'RUNNING_MODAL'}


# Panel
class COLMAP_PT_export_panel(bpy.types.Panel):
    bl_label = "COLMAP Export"
    bl_idname = "COLMAP_PT_export_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "output"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        settings = context.scene.colmap_export_settings
        scene = context.scene
        
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        # Info section
        box = layout.box()
        col = box.column(align=True)
        
        # Camera count
        scene_cameras = [i for i in scene.objects if i.type == "CAMERA"]
        camera_count = len(scene_cameras)
        
        row = col.row()
        row.alignment = 'LEFT'
        row.label(text=f"Cameras in Scene: {camera_count}", icon='CAMERA_DATA')
        
        if camera_count == 0:
            row = col.row()
            row.alert = True
            row.label(text="No cameras found!", icon='ERROR')
        
        # Mesh object count
        if settings.export_points and settings.points_selected_only:
            mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
            mesh_count = len(mesh_objects)
            row = col.row()
            row.alignment = 'LEFT'
            row.label(text=f"Selected Meshes: {mesh_count}", icon='MESH_DATA')
        else:
            mesh_objects = [obj for obj in scene.objects if obj.type == 'MESH']
            mesh_count = len(mesh_objects)
            row = col.row()
            row.alignment = 'LEFT'
            row.label(text=f"Mesh Objects: {mesh_count}", icon='MESH_DATA')
        
        layout.separator()
        
        # Settings
        col = layout.column(align=True)
        col.prop(settings, "output_path")
        col.prop(settings, "output_format")
        col.prop(settings, "render_images")
        col.prop(settings, "export_points")
        
        # Sub-option for points export
        if settings.export_points:
            row = col.row()
            row.prop(settings, "points_selected_only")
        
        layout.separator()
        
        # Export button
        row = layout.row()
        row.scale_y = 2.0
        
        if camera_count > 0:
            row.operator("colmap.export", text="Export COLMAP Dataset", icon='EXPORT')
        else:
            row.enabled = False
            row.operator("colmap.export", text="Export COLMAP Dataset", icon='ERROR')
        
        # Help text
        layout.separator()
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Quick Guide:", icon='INFO')
        col.separator(factor=0.5)
        col.label(text="1. Add cameras to your scene")
        col.label(text="2. Position cameras as needed")
        col.label(text="3. Set output directory above")
        col.label(text="4. Click 'Export COLMAP Dataset'")


# Registration
classes = (
    ColmapExportSettings,
    COLMAP_OT_export,
    COLMAP_PT_export_panel,
    )


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.colmap_export_settings = bpy.props.PointerProperty(
        type=ColmapExportSettings
    )


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Scene.colmap_export_settings


if __name__ == "__main__":
    register()
