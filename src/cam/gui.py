"""VisPy and PyQt5 frontend implementation."""
import sys
import numpy as np
from PyQt5 import QtWidgets, QtCore
from vispy import scene

from cam.config import AppConfig
from cam.graphics import create_heightmap, carve_toolpaths, get_skirt_mesh
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
        layout = QtWidgets.QHBoxLayout(central_widget)

        # Left Panel - Controls
        control_panel = QtWidgets.QWidget()
        control_panel.setFixedWidth(300)
        vbox = QtWidgets.QVBoxLayout(control_panel)
        layout.addWidget(control_panel)

        # Middle - Vispy Canvas
        self.canvas = scene.SceneCanvas(keys='interactive', show=True)
        self.view = self.canvas.central_widget.add_view()
        self.view.camera = 'turntable'
        self.view.camera.scale_factor = 200
        layout.addWidget(self.canvas.native)

        # Right Panel - GCode
        self.gcode_list = QtWidgets.QListWidget()
        self.gcode_list.setFixedWidth(280)
        self.gcode_list.addItems(self.state.gcode_lines)
        self.gcode_list.currentRowChanged.connect(self.on_listbox_changed)
        layout.addWidget(self.gcode_list)

        # Controls Setup
        nav_layout = QtWidgets.QHBoxLayout()
        btn_prev = QtWidgets.QPushButton("< Prev")
        btn_next = QtWidgets.QPushButton("Next >")
        btn_prev.clicked.connect(self.prev_step)
        btn_next.clicked.connect(self.next_step)
        nav_layout.addWidget(btn_prev)
        nav_layout.addWidget(btn_next)
        vbox.addLayout(nav_layout)

        vbox.addWidget(QtWidgets.QLabel("Line Step"))
        self.step_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.step_slider.setMinimum(0)
        self.step_slider.setMaximum(len(self.state.gcode_lines))
        self.step_slider.setValue(self.state.current_line)
        
        # Disable tracking: only emit valueChanged when the slider is released
        self.step_slider.setTracking(False) 
        
        self.step_slider.valueChanged.connect(self.slider_changed)
        vbox.addWidget(self.step_slider)

        # --- Add Debounce Timer ---
        self.debounce_timer = QtCore.QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(150) # 150ms delay
        self.debounce_timer.timeout.connect(self.update_canvas)

        vbox.addSpacing(20)
        vbox.addWidget(QtWidgets.QLabel("Stock Dimensions"))
        stock_layout = QtWidgets.QHBoxLayout()
        
        self.stock_x_input = QtWidgets.QDoubleSpinBox()
        self.stock_y_input = QtWidgets.QDoubleSpinBox()
        self.stock_z_input = QtWidgets.QDoubleSpinBox()
        
        for inp, val, label in zip(
            [self.stock_x_input, self.stock_y_input, self.stock_z_input],
            [self.state.stock_size_x, self.state.stock_size_y, self.state.stock_size_z],
            ["X", "Y", "Z"]
        ):
            inp_layout = QtWidgets.QVBoxLayout()
            inp_layout.addWidget(QtWidgets.QLabel(label))
            inp.setMaximum(10000.0)
            inp.setValue(val)
            inp.valueChanged.connect(self.stock_changed)
            inp_layout.addWidget(inp)
            stock_layout.addLayout(inp_layout)
            
        vbox.addLayout(stock_layout)
        vbox.addStretch()

        # Visuals setup
        self.stock_visual = scene.visuals.SurfacePlot(
            x=self.state.heightmap_x,
            y=self.state.heightmap_y,
            z=self.state.heightmap_z,
            color=(0.8, 0.8, 0.2, 1.0),
            parent=self.view.scene
        )
        
        # New Skirt Visual for solid rendering (darkened slightly for visual contrast)
        self.skirt_visual = scene.visuals.Mesh(
            color=(0.7, 0.7, 0.15, 1.0),
            parent=self.view.scene
        )

        self.rapid_lines = scene.visuals.Line(color='orange', method='gl', parent=self.view.scene)
        self.cut_lines = scene.visuals.Line(color='cyan', method='gl', parent=self.view.scene)
        
        scene.visuals.XYZAxis(parent=self.view.scene)

        self.update_canvas()

    def stock_changed(self):
        self.state.stock_size_x = self.stock_x_input.value()
        self.state.stock_size_y = self.stock_y_input.value()
        self.state.stock_size_z = self.stock_z_input.value()
        
        x, y, z = create_heightmap(self.state.stock_size_x, self.state.stock_size_y, resolution=self.state.stock_resolution)
        self.state.heightmap_x = x
        self.state.heightmap_y = y
        self.state.heightmap_z = z
        
        self.stock_visual.set_data(x=x, y=y, z=z)
        self.update_canvas()

    def prev_step(self):
        if self.state.current_line > 0:
            self.state.current_line -= 1
            self.step_slider.blockSignals(True)
            self.step_slider.setValue(self.state.current_line)
            self.step_slider.blockSignals(False)
            self.update_canvas() # Update instantly

    def next_step(self):
        if self.state.current_line < len(self.state.gcode_lines):
            self.state.current_line += 1
            self.step_slider.blockSignals(True)
            self.step_slider.setValue(self.state.current_line)
            self.step_slider.blockSignals(False)
            self.update_canvas() # Update instantly

    def slider_changed(self, value):
        self.state.current_line = value
        # Start (or restart) the debounce timer
        self.debounce_timer.start()

    def on_listbox_changed(self, row):
        self.state.current_line = row + 1
        self.step_slider.blockSignals(True)
        self.step_slider.setValue(self.state.current_line)
        self.step_slider.blockSignals(False)
        self.update_canvas()

    def update_canvas(self):
        # Update toolpaths limit
        max_idx = sum(1 for tp in self.state.toolpaths if tp[3] < self.state.current_line)
        
        # Update stock heightmap
        if self.state.heightmap_z is not None:
            carve_toolpaths(
                self.state.heightmap_z,
                self.state.heightmap_x,
                self.state.heightmap_y,
                self.state.toolpaths,
                max_idx,
                tool_radius=2.0
            )
            self.stock_visual.set_data(z=self.state.heightmap_z)
            
            # Update the solid skirt dynamically based on carved depth
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
            start, end, is_rapid, _ = self.state.toolpaths[i]
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

        # Update G-code list selection
        if 0 < self.state.current_line <= len(self.state.gcode_lines):
            self.gcode_list.blockSignals(True)
            self.gcode_list.setCurrentRow(self.state.current_line - 1)
            self.gcode_list.blockSignals(False)


def run_gui(config: AppConfig, state: AppState):
    """Entry point wrapper to run the frontend."""
    app = QtWidgets.QApplication(sys.argv)
    window = VispyFrontend(config, state)
    window.show()
    sys.exit(app.exec_())
