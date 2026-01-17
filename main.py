import sys, struct
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog,
    QTableWidget, QTableWidgetItem, QAction,
    QMessageBox, QComboBox, QLabel
)

ECUS = {
    "Janvar 7.2+": {
        "size": 524288,
        "maps": [
            ("Fuel Map", 393216, 16, 16, 0.01, 0.7, 1.3),
            ("Ignition Map", 393728, 16, 16, 0.1, -5, 45)
        ],
        "crc_addr": 0x1FFFC
    },
    "M73": {
        "size": 1048576,
        "maps": [
            ("Fuel VE", 786432, 16, 16, 0.01, 0.75, 1.25),
            ("Ignition", 787200, 16, 16, 0.1, -10, 50)
        ],
        "crc_addr": 0x3FFFC
    }
}

def calc_crc(data):
    return sum(data) & 0xFFFFFFFF

class ECUEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ECU Editor")
        self.resize(900, 600)

        self.table = QTableWidget()
        self.setCentralWidget(self.table)

        self.ecu_box = QComboBox()
        self.map_box = QComboBox()
        self.status = QLabel("Готово")

        self.ecu_box.addItems(ECUS.keys())
        self.ecu_box.currentTextChanged.connect(self.ecu_changed)
        self.map_box.currentIndexChanged.connect(self.map_changed)

        bar = self.menuBar()
        file_menu = bar.addMenu("Файл")
        open_act = QAction("Открыть BIN", self)
        save_act = QAction("Сохранить BIN", self)
        file_menu.addAction(open_act)
        file_menu.addAction(save_act)

        open_act.triggered.connect(self.open_fw)
        save_act.triggered.connect(self.save_fw)

        bar.addAction(self.ecu_box)
        bar.addAction(self.map_box)
        bar.setCornerWidget(self.status)

        self.fw = None
        self.current_map = None
        self.ecu_changed()

    def ecu_changed(self):
        self.map_box.clear()
        for m in ECUS[self.ecu_box.currentText()]["maps"]:
            self.map_box.addItem(m[0])

    def open_fw(self):
        path, _ = QFileDialog.getOpenFileName(self, "BIN", "", "*.bin")
        if not path:
            return
        with open(path, "rb") as f:
            self.fw = bytearray(f.read())

        ecu = ECUS[self.ecu_box.currentText()]
        if len(self.fw) != ecu["size"]:
            QMessageBox.critical(self, "Ошибка", "Неверный размер прошивки")
            self.fw = None
            return

        self.map_changed()
        self.status.setText("Прошивка загружена")

    def map_changed(self):
        if not self.fw:
            return
        ecu = ECUS[self.ecu_box.currentText()]
        name, addr, r, c, factor, _, _ = ecu["maps"][self.map_box.currentIndex()]
        self.current_map = ecu["maps"][self.map_box.currentIndex()]
        self.table.setRowCount(r)
        self.table.setColumnCount(c)

        raw = self.fw[addr:addr + r*c*2]
        vals = struct.unpack("<" + "H"*(r*c), raw)

        for y in range(r):
            for x in range(c):
                v = vals[y*c + x] * factor
                self.table.setItem(y, x, QTableWidgetItem(f"{v:.2f}"))

    def save_fw(self):
        if not self.fw or not self.current_map:
            return
        name, addr, r, c, factor, minv, maxv = self.current_map
        out = []

        for y in range(r):
            for x in range(c):
                try:
                    v = float(self.table.item(y, x).text())
                except:
                    QMessageBox.critical(self, "Ошибка", "Неверные данные")
                    return
                if not minv <= v <= maxv:
                    QMessageBox.critical(self, "Ошибка", f"{name}: опасное значение {v}")
                    return
                out.append(int(v / factor))

        raw = struct.pack("<" + "H"*len(out), *out)
        self.fw[addr:addr+len(raw)] = raw

        ecu = ECUS[self.ecu_box.currentText()]
        crc = calc_crc(self.fw[:-4])
        self.fw[ecu["crc_addr"]:ecu["crc_addr"]+4] = crc.to_bytes(4, "little")

        path, _ = QFileDialog.getSaveFileName(self, "Сохранить BIN", "", "*.bin")
        if path:
            with open(path, "wb") as f:
                f.write(self.fw)
            self.status.setText("Сохранено + CRC OK")

app = QApplication(sys.argv)
w = ECUEditor()
w.show()
sys.exit(app.exec_())
