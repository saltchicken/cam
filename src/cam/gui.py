"""VisPy and PyQt5 frontend implementation supporting Mill, Laser, and Pen modes."""
import sys
import numpy as np
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QPalette, QColor
from vispy import scene

from cam.config import AppConfig
from cam.graphics import create_heightmap, carve_toolpaths, get_skirt_mesh, generate_heightmap_colors
from cam.state import AppState


class VispyFrontend(QtWidgets.QMainWindow):

    def __init__(self, config: AppConfig, state: AppState):
        super().__init__()
        self.config = config
        self.state = state

        # Read mode from state (normalized to upper case)
        self.mode = getattr(self.state, 'mode', 'MILL').upper()

        self.setWindowTitle(self.config.window_title)
        self.resize(self.config.window_width, self.config.window_height)

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        
        # Main Layout
        main_layout = QtWidgets.QVBoxLayout(central_widget)

        # ==========================================
        # TOP VIEW: Canvas and G-Code List
        # ==========================================
        view_layout = QtWidgets.QHBoxLayout()
        main_layout.addLayout(view_layout)

        # Middle - Vispy Canvas
        self.canvas = scene.SceneCanvas(keys='interactive', show=True, bgcolor='#1e1e1e')
        self.view = self.canvas.central_widget.add_view()
        self.view.camera = 'turntable'
        self.view.camera.scale_factor = 200
        
        # Expand 3D view space
        view_layout.addWidget(self.canvas.native, stretch=1)

        # Right Panel - GCode
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

        # Nav Buttons
        nav_layout = QtWidgets.QHBoxLayout()
        btn_prev = QtWidgets.QPushButton("< Prev")
        btn_next = QtWidgets.QPushButton("Next >")
        btn_prev.clicked.connect(self.prev_step)
        btn_next.clicked.connect(self.next_step)
        nav_layout.addWidget(btn_prev)
        nav_layout.addWidget(btn_next)
        controls_layout.addLayout(nav_layout)

        # Line Step Slider
        slider_layout = QtWidgets.QVBoxLayout()
        slider_layout.addWidget(QtWidgets.QLabel("Line Step"))
        self.step_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.step_slider.setMinimum(0)
        self.step_slider.setMaximum(len(self.state.gcode_lines))
        self.step_slider.setValue(self.state.current_line)
        
        self.step_slider.valueChanged.connect(self.slider_changed)
        self.step_slider.sliderReleased.connect(self.update_canvas)
        slider_layout.addWidget(self.step_slider)
        controls_layout.addLayout(slider_layout)

        # Debounce Timer for Slider
        self.debounce_timer = QtCore.QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(150) # 150ms delay
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
        # Substrate definition base color based on active mode
        if self.mode == 'LASER':
            stock_color = (0.15, 0.15, 0.15, 1.0)  # Dark honeycomb bed / burn plate
            skirt_color = (0.2, 0.2, 0.2, 1.0)
            self.active_cut_color = '#ff3366'      # High visibility laser beam track
        elif self.mode == 'PEN':
            stock_color = (0.95, 0.95, 0.95, 1.0)  # White workspace paper
            skirt_color = (0.85, 0.85, 0.85, 1.0)
            self.active_cut_color = '#0066cc'      # Deep ink blue track
        else:
            stock_color = (0.8, 0.8, 0.2, 1.0)    # Traditional wood/polyurethane mill block
            skirt_color = (0.7, 0.7, 0.15, 1.0)
            self.active_cut_color = 'cyan'

        self.stock_visual = scene.visuals.SurfacePlot(
            x=self.state.heightmap_x,
            y=self.state.heightmap_y,
            z=self.state.heightmap_z,
            color=stock_color,
            parent=self.view.scene
        )
        
        self.skirt_visual = scene.visuals.Mesh(
            color=skirt_color,
            parent=self.view.scene
        )

        self.rapid_lines = scene.visuals.Line(color='orange', method='gl', parent=self.view.scene)
        self.cut_lines = scene.visuals.Line(color=self.active_cut_color, method='gl', parent=self.view.scene)
        
        scene.visuals.XYZAxis(parent=self.view.scene)

        self.update_canvas()

    def update_list_selection(self):
        """Immediately updates the highlighted row in the G-code listbox."""
        if 0 < self.state.current_line <= len(self.state.gcode_lines):
            self.gcode_list.blockSignals(True)
            self.gcode_list.setCurrentRow(self.state.current_line - 1)
            self.gcode_list.blockSignals(False)

    def closeEvent(self, event):
        """Save window state on close."""
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
        
        # Reset caching on size change
        self.state.last_carved_idx = 0
        
        self.stock_visual.set_data(x=x, y=y, z=z)
        self.update_canvas()

    def prev_step(self):
        if self.state.current_line > 0:
            self.state.current_line -= 1
            self.step_slider.blockSignals(True)
            self.step_slider.setValue(self.state.current_line)
            self.step_slider.blockSignals(False)
            
            self.update_list_selection()
            self.update_canvas()

    def next_step(self):
        if self.state.current_line < len(self.state.gcode_lines):
            self.state.current_line += 1
            self.step_slider.blockSignals(True)
            self.step_slider.setValue(self.state.current_line)
            self.step_slider.blockSignals(False)
            
            self.update_list_selection()
            self.update_canvas()

    def slider_changed(self, value):
        self.state.current_line = value
        self.update_list_selection()
        if not self.step_slider.isSliderDown():
            self.debounce_timer.start()

    def on_listbox_changed(self, row):
        self.state.current_line = row + 1
        self.step_slider.blockSignals(True)
        self.step_slider.setValue(self.state.current_line)
        self.step_slider.blockSignals(False)
        self.update_canvas()

    def update_canvas(self):
        max_idx = sum(1 for tp in self.state.toolpaths if tp[3] < self.state.current_line)
        
        if self.state.heightmap_z is not None:
            if self.mode in ('LASER', 'PEN'):
                # Surface modification bypass: keep substrate perfectly flat
                self.state.heightmap_z[:] = self.state.base_z_map[:]
                self.stock_visual.set_data(z=self.state.heightmap_z)
                self.state.last_carved_idx = max_idx
            else:
                # Standard MILL mode: Perform structural heightmap transformations
                if max_idx < self.state.last_carved_idx:
                    # Scrubbing backwards: Reset to flat stock and carve forward
                    self.state.heightmap_z[:] = self.state.base_z_map[:]
                    carve_toolpaths(
                        self.state.heightmap_z, self.state.heightmap_x, self.state.heightmap_y,
                        self.state.toolpaths, 0, max_idx, self.state.tool_diameter
                    )
                else:
                    # Scrubbing forwards: Calculate delta from last known position
                    carve_toolpaths(
                        self.state.heightmap_z, self.state.heightmap_x, self.state.heightmap_y,
                        self.state.toolpaths, self.state.last_carved_idx, max_idx, self.state.tool_diameter
                    )
                
                self.state.last_carved_idx = max_idx
                self.stock_visual.set_data(z=self.state.heightmap_z)
                
                # Apply Decoupled Vertex Colors for depth analysis
                vertices = self.stock_visual.mesh_data.get_vertices()
                colors = generate_heightmap_colors(vertices[:, 2], self.state.stock_size_z)
                self.stock_visual.mesh_data.set_vertex_colors(colors)
                self.stock_visual.mesh_data_changed()
            
            # Update the solid base envelope model
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
            # Fallback unpacking in case toolpaths contain mode-extended fields
            tp = self.state.toolpaths[i]
            start, end, is_rapid, _ = tp[0], tp[1], tp[2], tp[3]
            
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
    """Entry point wrapper to run the frontend."""
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
