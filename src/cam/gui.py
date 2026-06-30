import sys
import numpy as np
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QPalette, QColor
from vispy import scene

from cam.config import AppConfig
from cam.graphics import create_heightmap, get_skirt_mesh, generate_heightmap_colors
from cam.state import AppState


class VispyFrontend(QtWidgets.QMainWindow):

    def __init__(self, config: AppConfig, state: AppState):
        super().__init__()
        self.config = config
        self.state = state

        self.setWindowTitle(self.config.window_title)
        self.resize(self.config.window_width, self.config.window_height)

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QtWidgets.QVBoxLayout(central_widget)

        # ==========================================
        # TOP VIEW: Canvas and G-Code List
        # ==========================================
        view_layout = QtWidgets.QHBoxLayout()
        main_layout.addLayout(view_layout)

        self.canvas = scene.SceneCanvas(keys='interactive', show=True, bgcolor='#1e1e1e')
        self.view = self.canvas.central_widget.add_view()
        self.view.camera = 'turntable'
        self.view.camera.scale_factor = 200
        
        view_layout.addWidget(self.canvas.native, stretch=1)

        self.gcode_list = QtWidgets.QListWidget()
        self.gcode_list.setFixedWidth(280)
        self.gcode_list.addItems(self.state.gcode_lines)
        self.gcode_list.currentRowChanged.connect(self.on_listbox_changed)
        view_layout.addWidget(self.gcode_list)

        # ==========================================
        # BOTTOM PANEL: Controls Box
        # ==========================================
        control_panel = QtWidgets.QGroupBox("")
        controls_layout = QtWidgets.QHBoxLayout(control_panel)
        main_layout.addWidget(control_panel)

        # Navigation and Playback
        nav_layout = QtWidgets.QHBoxLayout()
        btn_prev = QtWidgets.QPushButton("< Step")
        self.btn_play = QtWidgets.QPushButton("Play")
        btn_next = QtWidgets.QPushButton("Step >")
        
        btn_prev.clicked.connect(self.prev_step)
        self.btn_play.clicked.connect(self.toggle_play)
        btn_next.clicked.connect(self.next_step)
        
        nav_layout.addWidget(btn_prev)
        nav_layout.addWidget(self.btn_play)
        nav_layout.addWidget(btn_next)
        controls_layout.addLayout(nav_layout)

        # Playback Timer setup
        self.play_timer = QtCore.QTimer()
        self.play_timer.setInterval(20)  # 20ms between steps for smooth animation
        self.play_timer.timeout.connect(self.animate_step)

        # Line Slider
        slider_layout = QtWidgets.QVBoxLayout()
        slider_layout.addWidget(QtWidgets.QLabel("Line Target"))
        self.step_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.step_slider.setMinimum(0)
        self.step_slider.setMaximum(len(self.state.gcode_lines))
        self.step_slider.setValue(self.state.current_line)
        
        self.step_slider.valueChanged.connect(self.slider_changed)
        self.step_slider.sliderReleased.connect(self.update_canvas)
        slider_layout.addWidget(self.step_slider)
        controls_layout.addLayout(slider_layout)

        self.debounce_timer = QtCore.QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(150)
        self.debounce_timer.timeout.connect(self.update_canvas)

        # Stock Dimensions
        stock_layout = QtWidgets.QHBoxLayout()
        stock_layout.addWidget(QtWidgets.QLabel("Stock Dimensions:"))
        
        self.stock_x_input = QtWidgets.QDoubleSpinBox()
        self.stock_y_input = QtWidgets.QDoubleSpinBox()
        self.stock_z_input = QtWidgets.QDoubleSpinBox()
        
        for inp, val, label in zip(
            [self.stock_x_input, self.stock_y_input, self.stock_z_input],
            [self.state.stock_size_x, self.state.stock_size_y, self.state.stock_size_z],
            ["X", "Y", "Z"]
        ):
            inp_layout = QtWidgets.QHBoxLayout()
            inp_layout.addWidget(QtWidgets.QLabel(label))
            inp.setMaximum(10000.0)
            inp.setValue(val)
            inp.valueChanged.connect(self.stock_changed)
            inp_layout.addWidget(inp)
            stock_layout.addLayout(inp_layout)
            
        controls_layout.addLayout(stock_layout)
        controls_layout.addStretch()

        # ==========================================
        # VISUALS SETUP 
        # ==========================================
        profile = self.state.profile

        self.stock_visual = scene.visuals.SurfacePlot(
            x=self.state.heightmap_x,
            y=self.state.heightmap_y,
            z=self.state.heightmap_z,
            color=profile.stock_color,
            parent=self.view.scene
        )
        
        self.skirt_visual = scene.visuals.Mesh(
            color=profile.skirt_color,
            parent=self.view.scene
        )

        self.rapid_lines = scene.visuals.Line(color='orange', method='gl', parent=self.view.scene)
        self.cut_lines = scene.visuals.Line(color=profile.cut_line_color, method='gl', parent=self.view.scene)
        
        scene.visuals.XYZAxis(parent=self.view.scene)
        self.update_canvas()

    # --- Sync Logic ---
    def sync_line_from_path(self):
        """Updates the slider and list UI to match the current toolpath index."""
        if self.state.current_path_idx == 0:
            self.state.current_line = 0
        else:
            # tp[3] is the original line index of this path
            tp = self.state.toolpaths[self.state.current_path_idx - 1]
            self.state.current_line = tp[3] + 1 

        self.step_slider.blockSignals(True)
        self.step_slider.setValue(self.state.current_line)
        self.step_slider.blockSignals(False)
        self.update_list_selection()

    def set_path_from_line(self):
        """Finds the first toolpath index that corresponds to the target line."""
        target_idx = len(self.state.toolpaths)
        for i, tp in enumerate(self.state.toolpaths):
            if tp[3] >= self.state.current_line - 1:
                target_idx = i
                break
        self.state.current_path_idx = target_idx

    def update_list_selection(self):
        if 0 < self.state.current_line <= len(self.state.gcode_lines):
            self.gcode_list.blockSignals(True)
            self.gcode_list.setCurrentRow(self.state.current_line - 1)
            self.gcode_list.blockSignals(False)

    def closeEvent(self, event):
        self.config.window_width = self.width()
        self.config.window_height = self.height()
        self.config.save()
        super().closeEvent(event)

    def stock_changed(self):
        self.state.stock_size_x = self.stock_x_input.value()
        self.state.stock_size_y = self.stock_y_input.value()
        self.state.stock_size_z = self.stock_z_input.value()
        
        x, y, z = create_heightmap(self.state.stock_size_x, self.state.stock_size_y, resolution=self.state.stock_resolution)
        self.state.heightmap_x = x
        self.state.heightmap_y = y
        self.state.heightmap_z = z
        self.state.base_z_map = z.copy()
        
        self.state.last_carved_idx = 0
        self.stock_visual.set_data(x=x, y=y, z=z)
        self.update_canvas()

    # --- Playback and Navigation ---
    def toggle_play(self):
        if self.play_timer.isActive():
            self.play_timer.stop()
            self.btn_play.setText("Play")
        else:
            self.play_timer.start()
            self.btn_play.setText("Pause")

    def animate_step(self):
        if self.state.current_path_idx < len(self.state.toolpaths):
            self.state.current_path_idx += 1
            self.sync_line_from_path()
            self.update_canvas()
        else:
            self.play_timer.stop()
            self.btn_play.setText("Play")

    def prev_step(self):
        if self.state.current_path_idx > 0:
            self.state.current_path_idx -= 1
            self.sync_line_from_path()
            self.update_canvas()

    def next_step(self):
        if self.state.current_path_idx < len(self.state.toolpaths):
            self.state.current_path_idx += 1
            self.sync_line_from_path()
            self.update_canvas()

    def slider_changed(self, value):
        self.state.current_line = value
        self.set_path_from_line()
        self.update_list_selection()
        if not self.step_slider.isSliderDown():
            self.debounce_timer.start()

    def on_listbox_changed(self, row):
        self.state.current_line = row + 1
        self.set_path_from_line()
        self.step_slider.blockSignals(True)
        self.step_slider.setValue(self.state.current_line)
        self.step_slider.blockSignals(False)
        self.update_canvas()

    # --- Core Renderer ---
    def update_canvas(self):
        # We now render directly based on the exact path step, instead of line chunks
        max_idx = self.state.current_path_idx
        
        if self.state.heightmap_z is not None:
            self.state.profile.update_heightmap(self.state, max_idx)
            self.state.last_carved_idx = max_idx
            self.stock_visual.set_data(z=self.state.heightmap_z)
            
            if self.state.profile.name == "MILL":
                vertices = self.stock_visual.mesh_data.get_vertices()
                colors = generate_heightmap_colors(vertices[:, 2], self.state.stock_size_z)
                self.stock_visual.mesh_data.set_vertex_colors(colors)
                self.stock_visual.mesh_data_changed()
            
            v, f = get_skirt_mesh(
                self.state.heightmap_x, 
                self.state.heightmap_y, 
                self.state.heightmap_z, 
                z_bottom=-self.state.stock_size_z
            )
            self.skirt_visual.set_data(vertices=v, faces=f)

        rapid_pts = []
        cut_pts = []

        for i in range(max_idx):
            tp = self.state.toolpaths[i]
            start, end, is_rapid = tp[0], tp[1], tp[2]
            
            if is_rapid:
                rapid_pts.extend([start, end])
            else:
                cut_pts.extend([start, end])

        if rapid_pts:
            self.rapid_lines.set_data(pos=np.array(rapid_pts, dtype=np.float32), connect='segments')
        else:
            self.rapid_lines.set_data(pos=np.zeros((0, 3), dtype=np.float32))

        if cut_pts:
            self.cut_lines.set_data(pos=np.array(cut_pts, dtype=np.float32), connect='segments')
        else:
            self.cut_lines.set_data(pos=np.zeros((0, 3), dtype=np.float32))


def run_gui(config: AppConfig, state: AppState):
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(43, 43, 43))
    dark_palette.setColor(QPalette.WindowText, QtCore.Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.AlternateBase, QColor(43, 43, 43))
    dark_palette.setColor(QPalette.ToolTipBase, QtCore.Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, QtCore.Qt.white)
    dark_palette.setColor(QPalette.Text, QtCore.Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(43, 43, 43))
    dark_palette.setColor(QPalette.ButtonText, QtCore.Qt.white)
    dark_palette.setColor(QPalette.BrightText, QtCore.Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, QtCore.Qt.black)
    dark_palette.setColor(QPalette.Disabled, QPalette.Text, QColor(127, 127, 127))
    dark_palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(127, 127, 127))
    
    app.setPalette(dark_palette)

    window = VispyFrontend(config, state)
    window.show()
    sys.exit(app.exec_())
