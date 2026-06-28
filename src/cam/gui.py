"""DearPyGui frontend implementation."""
import dearpygui.dearpygui as dpg

from cam.config import AppConfig
from cam.graphics import project_iso
from cam.state import AppState


class DpgFrontend:

    def __init__(self, config: AppConfig, state: AppState):
        self.config = config
        self.state = state

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

    def listbox_changed(self, _sender, app_data):
        try:
            self.state.current_line = self.state.gcode_lines.index(app_data) + 1
            dpg.set_value("step_slider", self.state.current_line)
            self.update_canvas()
        except ValueError:
            pass

    def on_resize(self, _sender, _app_data):
        vp_width = dpg.get_viewport_client_width()
        vp_height = dpg.get_viewport_client_height()

        if dpg.does_item_exist("drawlist"):
            dpg.set_item_width("drawlist", max(100, vp_width - 320))
            dpg.set_item_height("drawlist", max(100, vp_height - 80))

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

    # --- Main Rendering Loop ---

    def run(self):
        """Initializes and runs the DearPyGui application."""
        dpg.create_context()
        dpg.create_viewport(title=self.config.window_title,
                            width=self.config.window_width,
                            height=self.config.window_height)
        dpg.set_viewport_resize_callback(self.on_resize)

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
                            min_value=0.1,
                            max_value=20.0,
                            default_value=self.config.view_scale,
                            callback=self.view_changed,
                            user_data="scale",
                            width=120)
                        dpg.add_slider_float(
                            label="Offset X",
                            min_value=-5000.0,
                            max_value=5000.0,
                            default_value=self.config.view_offset_x,
                            callback=self.view_changed,
                            user_data="offset_x",
                            width=120)
                        dpg.add_slider_float(
                            label="Offset Y",
                            min_value=-5000.0,
                            max_value=5000.0,
                            default_value=self.config.view_offset_y,
                            callback=self.view_changed,
                            user_data="offset_y",
                            width=120)
                        dpg.add_slider_float(
                            label="Rot X",
                            min_value=-180.0,
                            max_value=180.0,
                            default_value=self.config.view_rot_x,
                            callback=self.view_changed,
                            user_data="rot_x",
                            width=120)
                        dpg.add_slider_float(
                            label="Rot Y",
                            min_value=-180.0,
                            max_value=180.0,
                            default_value=self.config.view_rot_y,
                            callback=self.view_changed,
                            user_data="rot_y",
                            width=120)
                        dpg.add_slider_float(
                            label="Rot Z",
                            min_value=-180.0,
                            max_value=180.0,
                            default_value=self.config.view_rot_z,
                            callback=self.view_changed,
                            user_data="rot_z",
                            width=120)

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
        dpg.start_dearpygui()
        dpg.destroy_context()


def run_gui(config: AppConfig, state: AppState):
    """Entry point wrapper to run the frontend."""
    app = DpgFrontend(config, state)
    app.run()
