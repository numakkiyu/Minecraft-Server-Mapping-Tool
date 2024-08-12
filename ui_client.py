import os
import json
import webbrowser
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QPushButton, QListWidget, QMessageBox, QInputDialog, \
    QHBoxLayout, QFileDialog, QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QListWidgetItem, QMenuBar, QAction
from PyQt5.QtCore import Qt
import core


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Minecraft服务器映射工具 v0.1.2")
        self.setGeometry(300, 100, 800, 600)

        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("文件")

        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menu_bar.addMenu("查看")

        visit_website_action = QAction("访问官网", self)
        visit_website_action.triggered.connect(self.visit_website)
        help_menu.addAction(visit_website_action)

        user_manual_action = QAction("使用方法", self)
        user_manual_action.triggered.connect(self.open_user_manual)
        help_menu.addAction(user_manual_action)

        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

        base_dir = os.path.abspath(os.path.dirname(__file__))
        qss_path = os.path.join(base_dir, 'assets', 'style.qss')

        # 创建映射文件夹
        self.mapping_dir = os.path.expanduser("~/.mapping")
        os.makedirs(self.mapping_dir, exist_ok=True)
        self.mapping_file = os.path.join(self.mapping_dir, "line.json")

        # 主界面布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.layout = QVBoxLayout(main_widget)

        # 显示映射服务器的列表
        self.mapping_list = QListWidget(self)
        self.layout.addWidget(self.mapping_list)

        # 按钮布局
        button_layout = QHBoxLayout()

        self.add_button = QPushButton("添加映射服务器", self)
        self.add_button.clicked.connect(self.add_mapping)
        button_layout.addWidget(self.add_button)

        self.start_button = QPushButton("开始映射", self)
        self.start_button.clicked.connect(self.start_selected_mapping)
        button_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("关闭映射", self)
        self.stop_button.clicked.connect(self.stop_selected_mapping)
        button_layout.addWidget(self.stop_button)

        self.remove_button = QPushButton("删除映射", self)
        self.remove_button.clicked.connect(self.remove_selected_mapping)
        button_layout.addWidget(self.remove_button)

        self.custom_json_button = QPushButton("加载服务器列表", self)
        self.custom_json_button.clicked.connect(self.load_custom_json)
        button_layout.addWidget(self.custom_json_button)

        self.load_button = QPushButton("从官网加载服务器列表", self)
        self.load_button.clicked.connect(self.load_servers_from_json)
        button_layout.addWidget(self.load_button)

        self.layout.addLayout(button_layout)

        if os.path.exists(qss_path):
            with open(qss_path, 'r') as f:
                self.setStyleSheet(f.read())

        self.mappings = []
        self.current_port = 25565

        self.load_mappings_from_file()

    def add_mapping(self):
        dialog = AddMappingDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            name, address = dialog.get_data()
            mapping = {"name": name, "address": address, "port": self.current_port, "active": False}
            self.mappings.append(mapping)
            self.update_mapping_list()
            self.current_port += 1
            self.save_mappings_to_file()

    def update_mapping_list(self):
        self.mapping_list.clear()
        for mapping in self.mappings:
            status = "开启" if mapping["active"] else "关闭"
            item_text = f"{mapping['name']} -> {mapping['address']} (端口: {mapping['port']}) - 映射: {status}"
            item = QListWidgetItem(item_text)
            self.mapping_list.addItem(item)

    def start_selected_mapping(self):
        selected_items = self.mapping_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, '警告', '没有选中任何映射!')
            return
        for item in selected_items:
            index = self.mapping_list.row(item)
            mapping = self.mappings[index]
            success = core.start_mapping(mapping['name'], mapping['address'], mapping['port'])
            if success:
                mapping["active"] = True
                self.update_mapping_list()
                self.save_mappings_to_file()
            else:
                QMessageBox.critical(self, '错误',
                                     f'无法启动映射: {mapping["name"]} ({mapping["address"]})，请检查服务器地址或网络连接。')

    def stop_selected_mapping(self):
        selected_items = self.mapping_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, '警告', '没有选中任何映射!')
            return
        for item in selected_items:
            index = self.mapping_list.row(item)
            mapping = self.mappings[index]
            core.stop_mapping(mapping['name'])
            mapping["active"] = False
            self.update_mapping_list()
            self.save_mappings_to_file()

    def remove_selected_mapping(self):
        selected_items = self.mapping_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, '警告', '没有选中任何映射!')
            return
        for item in selected_items:
            index = self.mapping_list.row(item)
            self.mapping_list.takeItem(index)
            mapping = self.mappings.pop(index)
            core.stop_mapping(mapping['name'])
            self.save_mappings_to_file()

    def load_servers_from_json(self):
        try:
            servers = core.get_servers_from_json()
            if servers:
                for server in servers:
                    mapping = {"name": server["name"], "address": server["dnip"], "port": self.current_port,
                               "active": False}
                    self.mappings.append(mapping)
                    self.update_mapping_list()
                    self.current_port += 1
                self.save_mappings_to_file()
            else:
                QMessageBox.warning(self, '获取失败', '未能获取到服务器列表。')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'获取服务器列表失败: {str(e)}')

    def load_custom_json(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择JSON文件", "", "JSON Files (*.json);;All Files (*)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    servers = json.load(file)
                    for server in servers:
                        mapping = {"name": server["name"], "address": server["dnip"], "port": self.current_port,
                                   "active": False}
                        self.mappings.append(mapping)
                        self.update_mapping_list()
                        self.current_port += 1
                    self.save_mappings_to_file()
            except Exception as e:
                QMessageBox.critical(self, '错误', f'加载本地JSON文件失败: {str(e)}')

    def load_mappings_from_file(self):
        if os.path.exists(self.mapping_file):
            try:
                with open(self.mapping_file, 'r', encoding='utf-8') as file:
                    mappings = json.load(file)
                    for mapping in mappings:
                        self.mappings.append(
                            {"name": mapping["name"], "address": mapping["dnip"], "port": self.current_port,
                             "active": False})
                        self.current_port += 1
                    self.update_mapping_list()
            except Exception as e:
                QMessageBox.critical(self, '错误', f'加载映射文件失败: {str(e)}')

    def save_mappings_to_file(self):
        try:
            mappings_to_save = [{"name": m["name"], "dnip": m["address"]} for m in self.mappings]
            with open(self.mapping_file, 'w', encoding='utf-8') as file:
                json.dump(mappings_to_save, file, ensure_ascii=False, indent=4)
        except Exception as e:
            QMessageBox.critical(self, '错误', f'保存映射文件失败: {str(e)}')

    def visit_website(self):
        webbrowser.open("你的网站地址")

    def open_user_manual(self):
        webbrowser.open("你的文档地址")

    def show_about_dialog(self):
        QMessageBox.about(self, "关于", "Minecraft服务器映射工具\n版本: v0.1.2\n版权所有 © 2024 北海的佰川（BHCN)")
        # 你可以自己添加，但绝对不能删掉


class AddMappingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('添加映射服务器')
        self.layout = QVBoxLayout(self)

        form_layout = QFormLayout()
        self.name_edit = QLineEdit(self)
        self.address_edit = QLineEdit(self)
        form_layout.addRow('服务器名称:', self.name_edit)
        form_layout.addRow('服务器地址:', self.address_edit)
        self.layout.addLayout(form_layout)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

    def get_data(self):
        return self.name_edit.text(), self.address_edit.text()
