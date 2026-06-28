"""DearPyGui frontend implementation."""
import dearpygui.dearpygui as dpg

from cam.config import AppConfig
from cam.graphics import project_iso, generate_stock
from cam.state import AppState


class DpgFrontend:

    def __init__(self, config: AppConfig, state: AppState):
        self.config = config
        self.state = state
        self.last_mouse_pos = None
        self.is_dragging_left = False
        self.is_dragging_right = False

    def _project(self, x, y, z):
        """Helper to project 3D coordinates using the current view configuration."""
        return project_iso(x, y, z, 
                           self.config.view_scale, 
                           self.config.view_offset_x, 
                           self.config.view_offset_y,
                           self.config.view_rot_x,
                           self.config.view_rot_y,
                           self.config.view_rot_z)

    def update_canvas(self):
        """Clears the drawlist and redraws paths up to current_line."""
        dpg.delete_item("drawlist", children_only=True)

        self.draw_origin(axis_length=30.0)
        self.draw_stock()

        max_idx = sum(
            1 for tp in self.state.toolpaths if tp[3] < self.state.current_line)

        if 0 < self.state.current_line <= len(self.state.gcode_lines):
            text = self.state.gcode_lines[self.state.current_line - 1]
            dpg.set_value("gcode_listbox", text)
        else:
            if self.state.gcode_lines:
                dpg.set_value("gcode_listbox", self.state.gcode_lines[0])

        for i in range(max_idx):
            start, end, is_rapid, _ = self.state.toolpaths[i]
            p1 = self._project(*start)
            p2 = self._project(*end)

            color = [255, 140, 0, 200] if is_rapid else [0, 255, 255, 255]
            thickness = 1 if is_rapid else 2

            dpg.draw_line(p1,
                          p2,
                          color=color,
                          thickness=thickness,
                          parent="drawlist")

    # --- UI Callbacks ---

    def next_step(self, _sender=None, _app_data=None):
        if self.state.current_line < len(self.state.gcode_lines):
            self.state.current_line += 1
            dpg.set_value("step_slider", self.state.current_line)
            self.update_canvas()

    def prev_step(self, _sender=None, _app_data=None):
        if self.state.current_line > 0:
            self.state.current_line -= 1
            dpg.set_value("step_slider", self.state.current_line)
            self.update_canvas()

    def slider_changed(self, _sender, app_data):
        self.state.current_line = app_data
        self.update_canvas()

    def view_changed(self, _sender, app_data, user_data):
        if user_data == "scale":
            self.config.view_scale = app_data
        elif user_data == "offset_x":
            self.config.view_offset_x = app_data
        elif user_data == "offset_y":
            self.config.view_offset_y = app_data
        elif user_data == "rot_x":
            self.config.view_rot_x = app_data
        elif user_data == "rot_y":
            self.config.view_rot_y = app_data
        elif user_data == "rot_z":
            self.config.view_rot_z = app_data
        self.update_canvas()
        
    def stock_changed(self, _sender, app_data, user_data):
        """Updates the stock geometry when a user changes the dimensions."""
        if user_data == "stock_x":
            self.state.stock_size_x = app_data
        elif user_data == "stock_y":
            self.state.stock_size_y = app_data
        elif user_data == "stock_z":
            self.state.stock_size_z = app_data
            
        # Regenerate the vertices and faces based on the new sizes
        verts, faces = generate_stock(
            self.state.stock_size_x, 
            self.state.stock_size_y, 
            self.state.stock_size_z
        )
        self.state.stock_vertices = verts
        self.state.stock_faces = faces
        
        self.update_canvas()

    def listbox_changed(self, _sender, app_data):
        try:
            self.state.current_line = self.state.gcode_lines.index(app_data) + 1
            dpg.set_value("step_slider", self.state.current_line)
            self.update_canvas()
        except ValueError:
            pass

    def _sync_view_sliders(self):
        if dpg.does_item_exist("scale_slider"):
            dpg.set_value("scale_slider", self.config.view_scale)
            dpg.set_value("offset_x_slider", self.config.view_offset_x)
            dpg.set_value("offset_y_slider", self.config.view_offset_y)
            dpg.set_value("rot_x_slider", self.config.view_rot_x)
            dpg.set_value("rot_y_slider", self.config.view_rot_y)
            dpg.set_value("rot_z_slider", self.config.view_rot_z)

    def on_mouse_move(self, _sender, app_data):
        current_pos = app_data
        
        hovering_canvas = dpg.does_item_exist("drawlist") and dpg.is_item_hovered("drawlist")
        
        if dpg.is_mouse_button_down(0):
            if hovering_canvas and not self.is_dragging_left:
                self.is_dragging_left = True
        else:
            self.is_dragging_left = False
            
        if dpg.is_mouse_button_down(1) or dpg.is_mouse_button_down(2):
            if hovering_canvas and not self.is_dragging_right:
                self.is_dragging_right = True
        else:
            self.is_dragging_right = False

        if self.last_mouse_pos is not None:
            dx = current_pos[0] - self.last_mouse_pos[0]
            dy = current_pos[1] - self.last_mouse_pos[1]
            
            if self.is_dragging_left:
                self.config.view_rot_z -= dx * 0.5
                self.config.view_rot_x -= dy * 0.5
                
                if self.config.view_rot_x > 180: self.config.view_rot_x -= 360
                if self.config.view_rot_x < -180: self.config.view_rot_x += 360
                if self.config.view_rot_z > 180: self.config.view_rot_z -= 360
                if self.config.view_rot_z < -180: self.config.view_rot_z += 360
                
                self._sync_view_sliders()
                self.update_canvas()
            elif self.is_dragging_right:
                self.config.view_offset_x += dx
                self.config.view_offset_y += dy
                self._sync_view_sliders()
                self.update_canvas()

        self.last_mouse_pos = current_pos

    def on_mouse_wheel(self, _sender, app_data):
        if dpg.does_item_exist("drawlist") and dpg.is_item_hovered("drawlist"):
            zoom_factor = 1.0 + (app_data * 0.1)
            self.config.view_scale *= zoom_factor
            self.config.view_scale = max(0.01, min(self.config.view_scale, 100.0))
            self._sync_view_sliders()
            self.update_canvas()

    def on_resize(self, _sender, _app_data):
        vp_width = dpg.get_viewport_client_width()
        vp_height = dpg.get_viewport_client_height()

        if dpg.does_item_exist("drawlist"):
            dpg.set_item_width("drawlist", max(100, vp_width - 320))
            dpg.set_item_height("drawlist", max(100, vp_height - 180))

        if dpg.does_item_exist("gcode_listbox"):
            dpg.configure_item("gcode_listbox",
                               num_items=max(3, (vp_height - 40) // 18))

    def draw_origin(self, axis_length=25.0):
        """Draws an RGB coordinate triad at (0,0,0) to indicate the origin."""
        # Define the 3D points for the origin and the tips of the axes
        orig_3d = (0.0, 0.0, 0.0)
        x_3d = (axis_length, 0.0, 0.0)
        y_3d = (0.0, axis_length, 0.0)
        z_3d = (0.0, 0.0, axis_length)

        # Project the 3D points to 2D screen coordinates
        orig_2d = self._project(*orig_3d)
        x_2d = self._project(*x_3d)
        y_2d = self._project(*y_3d)
        z_2d = self._project(*z_3d)

        if dpg.does_item_exist("drawlist"):
            # X-Axis (Red)
            dpg.draw_line(orig_2d,
                          x_2d,
                          color=[255, 70, 70, 255],
                          thickness=3,
                          parent="drawlist")
            dpg.draw_text(x_2d,
                          "X",
                          color=[255, 70, 70, 255],
                          size=16,
                          parent="drawlist")

            # Y-Axis (Green)
            dpg.draw_line(orig_2d,
                          y_2d,
                          color=[70, 255, 70, 255],
                          thickness=3,
                          parent="drawlist")
            dpg.draw_text(y_2d,
                          "Y",
                          color=[70, 255, 70, 255],
                          size=16,
                          parent="drawlist")

            # Z-Axis (Blue)
            dpg.draw_line(orig_2d,
                          z_2d,
                          color=[70, 150, 255, 255],
                          thickness=3,
                          parent="drawlist")
            dpg.draw_text(z_2d,
                          "Z",
                          color=[70, 150, 255, 255],
                          size=16,
                          parent="drawlist")

            # Draw a solid white dot exactly at (0, 0, 0)
            dpg.draw_circle(orig_2d,
                            radius=4,
                            color=[255, 255, 255, 255],
                            fill=[255, 255, 255, 255],
                            parent="drawlist")
        else:
            print("draw_origin error. drawlist does not exist")

    def draw_stock(self):
        """Draws the stock material object onto the drawlist."""
        if not self.state.stock_vertices or not dpg.does_item_exist("drawlist"):
            return

        for face in self.state.stock_faces:
            # Project all 3D vertices of this face to 2D
            pts_2d = [self._project(*self.state.stock_vertices[i]) for i in face]
            
            # Close the loop for the wireframe
            pts_2d.append(pts_2d[0]) 

            dpg.draw_polyline(
                pts_2d,
                color=[200, 200, 50, 150],  # Translucent yellow/gold for stock
                thickness=1,
                parent="drawlist"
            )

    # --- Main Rendering Loop ---

    def run(self):
        """Initializes and runs the DearPyGui application."""
        dpg.create_context()
        dpg.create_viewport(title=self.config.window_title,
                            width=self.config.window_width,
                            height=self.config.window_height)
        dpg.set_viewport_resize_callback(self.on_resize)

        with dpg.handler_registry():
            dpg.add_mouse_move_handler(callback=self.on_mouse_move)
            dpg.add_mouse_wheel_handler(callback=self.on_mouse_wheel)

        with dpg.window(tag="primary_window"):
            with dpg.group(horizontal=True):

                # Left Panel (Controls + Canvas)
                with dpg.child_window(width=-300, height=-1, border=False):
                    with dpg.group(horizontal=True):
                        dpg.add_button(label="< Prev", callback=self.prev_step)
                        dpg.add_button(label="Next >", callback=self.next_step)
                        dpg.add_slider_int(
                            label="Line",
                            tag="step_slider",
                            min_value=0,
                            max_value=len(self.state.gcode_lines),
                            default_value=self.state.current_line,
                            callback=self.slider_changed,
                            width=250)

                    with dpg.group(horizontal=True):
                        dpg.add_slider_float(
                            label="Scale",
                            tag="scale_slider",
                            min_value=0.1,
                            max_value=100.0,
                            default_value=self.config.view_scale,
                            callback=self.view_changed,
                            user_data="scale",
                            width=120)
                        dpg.add_slider_float(
                            label="Offset X",
                            tag="offset_x_slider",
                            min_value=-5000.0,
                            max_value=5000.0,
                            default_value=self.config.view_offset_x,
                            callback=self.view_changed,
                            user_data="offset_x",
                            width=120)
                        dpg.add_slider_float(
                            label="Offset Y",
                            tag="offset_y_slider",
                            min_value=-5000.0,
                            max_value=5000.0,
                            default_value=self.config.view_offset_y,
                            callback=self.view_changed,
                            user_data="offset_y",
                            width=120)
                        dpg.add_slider_float(
                            label="Rot X",
                            tag="rot_x_slider",
                            min_value=-180.0,
                            max_value=180.0,
                            default_value=self.config.view_rot_x,
                            callback=self.view_changed,
                            user_data="rot_x",
                            width=120)
                        dpg.add_slider_float(
                            label="Rot Y",
                            tag="rot_y_slider",
                            min_value=-180.0,
                            max_value=180.0,
                            default_value=self.config.view_rot_y,
                            callback=self.view_changed,
                            user_data="rot_y",
                            width=120)
                        dpg.add_slider_float(
                            label="Rot Z",
                            tag="rot_z_slider",
                            min_value=-180.0,
                            max_value=180.0,
                            default_value=self.config.view_rot_z,
                            callback=self.view_changed,
                            user_data="rot_z",
                            width=120)

                    dpg.add_separator()
                    
                    # Stock Settings UI
                    dpg.add_text("Stock Dimensions")
                    with dpg.group(horizontal=True):
                        dpg.add_input_float(
                            label="Width (X)", 
                            default_value=self.state.stock_size_x,
                            callback=self.stock_changed,
                            user_data="stock_x",
                            width=100
                        )
                        dpg.add_input_float(
                            label="Height (Y)", 
                            default_value=self.state.stock_size_y,
                            callback=self.stock_changed,
                            user_data="stock_y",
                            width=100
                        )
                        dpg.add_input_float(
                            label="Depth (Z)", 
                            default_value=self.state.stock_size_z,
                            callback=self.stock_changed,
                            user_data="stock_z",
                            width=100
                        )

                    dpg.add_separator()

                    with dpg.drawlist(tag="drawlist", width=700, height=650):
                        pass

                # Right Panel (G-Code List)
                with dpg.child_window(width=280, height=-1, border=False):
                    dpg.add_listbox(items=self.state.gcode_lines,
                                    tag="gcode_listbox",
                                    width=-1,
                                    num_items=35,
                                    callback=self.listbox_changed)

        self.update_canvas()
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window("primary_window", True)
        self.on_resize(None, None)
        dpg.start_dearpygui()
        dpg.destroy_context()


def run_gui(config: AppConfig, state: AppState):
    """Entry point wrapper to run the frontend."""
    app = DpgFrontend(config, state)
    app.run()
