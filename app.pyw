import sys
import subprocess
import configparser
import os
import re
import threading
import time
import webbrowser
import atexit
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QLabel, 
                            QLineEdit, QVBoxLayout, QHBoxLayout, QWidget, 
                            QTextEdit, QMessageBox, QFrame)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QFont, QColor, QTextCursor
from datetime import datetime

# 新增：单实例支持模块
import platform
if platform.system() == 'Windows':
    import win32event
    import win32api
else:
    import fcntl

class SingleInstance:
    """单实例控制类 - 确保应用程序在系统中只运行一个实例"""
    
    def __init__(self, app_name="糯米茨内网穿透工具"):
        self.app_name = app_name
        self.locked = False
        self.lock_handle = None
        
    def acquire_lock(self):
        """获取应用程序锁"""
        if platform.system() == 'Windows':
            # Windows系统使用命名互斥体
            mutex_name = f'Local\\{self.app_name}'
            self.lock_handle = win32event.CreateMutex(None, 1, mutex_name)
            error = win32api.GetLastError()
            
            if error == 183:  # ERROR_ALREADY_EXISTS
                return False
            self.locked = True
        else:
            # Unix/Linux/Mac系统使用文件锁
            lock_file = f'/tmp/{self.app_name}.lock'
            self.lock_file = open(lock_file, 'w')
            try:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.locked = True
                # 程序退出时删除锁文件
                atexit.register(self.release_lock)
            except IOError:
                return False
        
        return self.locked
    
    def release_lock(self):
        """释放应用程序锁"""
        if self.locked:
            if platform.system() == 'Windows':
                if self.lock_handle:
                    win32event.ReleaseMutex(self.lock_handle)
            else:
                if hasattr(self, 'lock_file') and self.lock_file:
                    fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                    self.lock_file.close()
                    try:
                        os.unlink(self.lock_file.name)
                    except:
                        pass
            self.locked = False

class ConfigManager:
    """配置文件管理类 - 负责保存和读取用户配置"""
    
    def __init__(self, config_file="user_config.ini"):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        
    def save_config(self, name, local_port, remote_port):
        """保存用户配置"""
        try:
            self.config['UserSettings'] = {
                'name': name,
                'local_port': local_port,
                'remote_port': remote_port
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as configfile:
                self.config.write(configfile)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def load_config(self):
        """加载用户配置"""
        try:
            if os.path.exists(self.config_file):
                self.config.read(self.config_file, encoding='utf-8')
                if 'UserSettings' in self.config:
                    settings = self.config['UserSettings']
                    return {
                        'name': settings.get('name', ''),
                        'local_port': settings.get('local_port', ''),
                        'remote_port': settings.get('remote_port', '')
                    }
        except Exception as e:
            print(f"加载配置失败: {e}")
        return {'name': '', 'local_port': '', 'remote_port': ''}

class LogManager:
    """日志文件管理类 - 负责创建和管理日志文件"""
    
    def __init__(self, log_dir="log"):
        self.log_dir = log_dir
        self.app_log_file = None
        self.frpc_log_file = None
        
        self.create_log_directory()
        self.init_log_files()
    
    def create_log_directory(self):
        """创建日志目录"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            print(f"创建日志目录: {self.log_dir}")
    
    def init_log_files(self):
        """初始化日志文件，处理文件名冲突"""
        
        app_log_path = self.get_incremented_filename(self.log_dir, "log", "txt")
        frpc_log_path = self.get_incremented_filename(self.log_dir, "frpc", "log")
        
        self.app_log_file = open(app_log_path, "w", encoding="utf-8")
        self.frpc_log_file = open(frpc_log_path, "w", encoding="utf-8")
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.app_log_file.write(f"应用日志文件创建于: {now}\n")
        self.frpc_log_file.write(f"FRPC原始日志文件创建于: {now}\n")
        
        print(f"应用日志文件: {app_log_path}")
        print(f"FRPC原始日志文件: {frpc_log_path}")
    
    def get_incremented_filename(self, directory, base_name, extension, max_files=5):
        """获取递增的文件名，处理文件冲突，限制最大文件数"""
        
        file_path = os.path.join(directory, f"{base_name}.{extension}")
        if not os.path.exists(file_path):
            return file_path
        
        existing_files = []
        pattern = re.compile(rf"{base_name}(\d+)\.{extension}")
        
        for filename in os.listdir(directory):
            match = pattern.match(filename)
            if match:
                num = int(match.group(1))
                existing_files.append((num, filename))
        
        if len(existing_files) >= max_files:
            existing_files.sort(key=lambda x: x[0])
            for num, filename in existing_files[:len(existing_files) - max_files + 1]:
                os.remove(os.path.join(directory, filename))
        
        if existing_files:
            max_num = max(num for num, _ in existing_files)
            return os.path.join(directory, f"{base_name}{max_num + 1}.{extension}")
        else:
            return os.path.join(directory, f"{base_name}1.{extension}")
    
    def write_app_log(self, message):
        """写入应用程序格式化日志"""
        if self.app_log_file:
            clean_message = re.sub(r'<[^>]+>', '', message)
            self.app_log_file.write(f"{clean_message}\n")
            self.app_log_file.flush()
    
    def write_frpc_log(self, message):
        """写入FRPC原始日志"""
        if self.frpc_log_file:
            self.frpc_log_file.write(f"{message}\n")
            self.frpc_log_file.flush()
    
    def close(self):
        """关闭日志文件"""
        if self.app_log_file:
            self.app_log_file.close()
            self.app_log_file = None
        
        if self.frpc_log_file:
            self.frpc_log_file.close()
            self.frpc_log_file = None

class FRPThread(QThread):
    """FRP进程线程 - 负责运行FRP客户端并处理日志"""
    
    status_updated = pyqtSignal(str)
    log_updated = pyqtSignal(str)
    process_finished = pyqtSignal()
    
    proxy_started = pyqtSignal(str)
    LOG_TRANSLATION = {
        "start proxy success": "代理启动成功",
        "start reverse proxy success": "反向代理启动成功",
        "heart beat to server timeout": "与服务器的心跳连接超时",
        "connect to server failed": "连接服务器失败",
        "reconnect to server": "正在重新连接服务器",
        "reconnect success": "重新连接成功",
        "client version": "客户端版本",
        "server version": "服务器版本",
        "login to server success": "登录服务器成功",
        "try to connect to server...": "正在尝试连接服务器...",
        ", get run id ": ", 获取运行ID ",
        "login to server success": "登录服务器成功",
        "port unavailable": "端口已被使用，请联系糯米茨进行询问",
        "TCP proxy listen port": "TCP代理监听端口",
        "start error": "启动错误",
        "proxy removed": "代理已移除",
        "new proxy added": "新代理已添加",
        "error": "错误",
        "timeout": "超时",
        "closed": "已关闭",
        "restart": "重启",
        "stopping": "正在停止",
        "stopped": "已停止",
        "started": "已启动",
        "listening": "正在监听",
        "[I]": "[信息]",
        "[W]": "[警告]",
        "[E]": "[错误]",
        "start frpc service for config file": "启动配置文件的frpc服务",
        "proxy added": "已添加代理",
        "WARNING: ini format is deprecated": "警告：ini格式已过时",
        "please use yaml/json/toml format instead": "请改用yaml/json/toml格式",
         "connect to server 错误: dial tcp: lookup": "连接服务器错误: 找不到！",
        "no such host": "主机不存在。问题出在给你找个应用的人身上拿，去找他吧",
        "frpc service for config file": "配置文件的frpc服务",
        "login to the server failed: dial tcp: lookup": "登录服务器失败: 找不到！",
        "With loginFailExit enabled, no additional retries will be attempted": "已启用登录失败退出，不会尝试额外的重试",
        "connect to server 错误: dial tcp": "连接服务器错误: TCP链接失败。请找服务器管理员确认服务器是否正常运行。",
        "connectex: No connection could be made because the target machine actively refused it.": "连接被目标机器主动拒绝。原因推测：服务器的防火墙没有开放，或者服务器的域名或IP已过期。",
        "login to the server failed: dial tcp": "登录服务器失败: TCP链接失败。请找服务器管理员确认服务器是否正常运行。",

    }
    
    LOG_CATEGORIES = {
        "success": "成功",
        "error": "错误",
        "timeout": "超时",
        "warning": "警告",
        "info": "信息",
        "connect": "连接",
        "reconnect": "重连",
        "login": "登录",
        "proxy": "代理",
        "heart": "心跳",
        "client": "客户端",
        "server": "服务器",
        "version": "版本",
        "start": "启动",
        "stop": "停止",
        "listen": "监听",
        "removed": "移除",
        "added": "添加",
        "get": "获取",
        "deprecate": "弃用",
        "warning": "警告",
        "service": "服务",
        "control": "控制",
        "manager": "管理",
    }

    def __init__(self, frpc_path, config_path, log_manager):
        super().__init__()
        self.frpc_path = frpc_path
        self.config_path = config_path
        self.log_manager = log_manager
        self.process = None
        self.running = False
        
        self.remote_port_pattern = re.compile(r'remote_port\s*=\s*(\d+)')
        self.remote_port = None
        
        self.read_remote_port()

    def read_remote_port(self):
        """读取配置文件获取远程端口"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    content = f.read()
                    match = self.remote_port_pattern.search(content)
                    if match:
                        self.remote_port = match.group(1)
        except Exception as e:
            print(f"读取配置文件失败: {e}")

    def run(self):
        """线程运行函数 - 启动FRP进程并处理输出"""
        self.running = True
        self.status_updated.emit("在线")
        try:
            self.process = subprocess.Popen(
                [self.frpc_path, '-c', self.config_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            for line in iter(self.process.stdout.readline, ''):
                if not self.running:
                    break
                
                self.log_manager.write_frpc_log(line.strip())
                
                formatted_line = self.format_log(line.strip())
                self.log_updated.emit(formatted_line)
                
                self.log_manager.write_app_log(formatted_line)
                
                if "代理启动成功" in formatted_line:
                    if self.remote_port:
                        self.proxy_started.emit(self.remote_port)
            
            self.process.wait()
        except Exception as e:
            error_msg = self.format_log(f"错误: {str(e)}")
            self.log_updated.emit(error_msg)
            self.log_manager.write_app_log(error_msg)
            self.log_manager.write_frpc_log(f"错误: {str(e)}")
        finally:
            self.running = False
            self.status_updated.emit("离线")
            self.process_finished.emit()

    def get_log_category(self, log_line):
        """确定日志的类别"""
        lower_line = log_line.lower()
        
        for component in ["client", "server", "proxy", "heart", "service", "control", "manager"]:
            if f"[{component}]" in log_line or f"[{component}." in log_line:
                return self.LOG_CATEGORIES.get(component, "信息")
        
        for keyword, category in self.LOG_CATEGORIES.items():
            if keyword in lower_line:
                return category
        
        return "信息"  

    def format_log(self, log_line):
        """格式化日志输出"""
        
        current_time = datetime.now().strftime("%H:%M:%S")
        
        clean_line = self.remove_ansi_and_timestamp(log_line)
        
        translated_line = self.advanced_translate_log(clean_line)
        
        category = self.get_log_category(translated_line)
        
        formatted_log = f"[{current_time}][{category}]{translated_line}"
        return formatted_log

    def remove_ansi_and_timestamp(self, log_line):
        """移除ANSI转义序列和原始时间戳"""
        
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        clean_line = ansi_escape.sub('', log_line)
        
        timestamp_pattern = re.compile(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+')
        clean_line = timestamp_pattern.sub('', clean_line).strip()
        
        module_pattern = re.compile(r'\[[a-z/]+.go:\d+\]')
        clean_line = module_pattern.sub('', clean_line).strip()
        
        return clean_line

    def advanced_translate_log(self, log_line):
        """增强版日志翻译方法"""
        
        log_levels = {
            "[I]": "[信息]",
            "[W]": "[警告]",
            "[E]": "[错误]",
            "[D]": "[调试]",
        }
        
        for level, translation in log_levels.items():
            if level in log_line:
                log_line = log_line.replace(level, translation)
        
        patterns = [
            (r'(\[.*?\]) login to server success, get run id \[(.*?)\]', r'\1 登录服务器成功, 获取运行ID [\2]'),
            (r'(\[.*?\]) proxy added: \[(.*?)\]', r'\1 已添加代理: [\2]'),
            (r'(\[.*?\]) \[(.*?)\] start proxy success', r'\1 [\2] 代理启动成功'),
            (r'start frpc service for config file \[(.*?)\]', r'启动配置文件 [\1] 的frpc服务'),
            (r'(\[.*?\]) \[(.*?)\] start error: proxy \[(.*?)\] already exists', r'\1 [\2] 启动错误: 代理 [\3] 已存在'),
            (r'(\[.*?\])\[.*?\] connect to server 错误: dial tcp: lookup (.*?): no such host', r'\1 连接服务器错误: 无法解析主机名 [\2]可能是给你这个应用的人搞错了设置'),
            (r'(\[.*?\])\[.*?\] frpc service for config file \[(.*?)\] 已停止', r'\1 配置文件 [\2] 的frpc服务已停止'),
            (r'(\[.*?\])login to the server failed: dial tcp: lookup (.*?): no such host.', r'\1 登录服务器失败: 无法解析主机名 [\2]同上，去找他看看吧'),
            (r'(\[.*?\])With loginFailExit enabled, no additional retries will be attempted', r'\1 已启用登录失败退出，不会尝试额外的重试'),
            (r'(\[.*?\])\[.*?\] connect to server 错误: dial tcp (.*?): connectex: No connection could be made because the target machine actively refused it.', r'\1 连接服务器错误: 目标地址 [\2] 拒绝连接。原因推测：服务器的防火墙没有开放，或者服务器的域名或IP已过期。'),
            (r'(\[.*?\])login to the server failed: dial tcp (.*?): connectex: No connection could be made because the target machine actively refused it.', r'\1 登录服务器失败: 目标地址 [\2] 拒绝连接。请找服务器管理员确认服务器是否正常运行。'),


        ]
        
        for pattern, replacement in patterns:
            if re.search(pattern, log_line):
                return re.sub(pattern, replacement, log_line)
        
        for en_phrase, cn_phrase in self.LOG_TRANSLATION.items():
            if en_phrase in log_line:
                log_line = log_line.replace(en_phrase, cn_phrase)
        
        return log_line

    def stop(self):
        """停止FRP进程"""
        if self.process and self.running:
            self.running = False
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()

class MainWindow(QMainWindow):
    """主窗口类 - 应用程序的主要界面"""
    
    def __init__(self):
        super().__init__()
        
        if hasattr(Qt, 'AA_EnableHighDpiScaling'):
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        
        self.setWindowTitle("糯米茨的内网穿透工具")
        self.setGeometry(100, 100, 800, 500)  
        
        icon_path = "icon.ico"
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.frpc_path = "frpc.exe"
        self.config_path = "frpc.ini"  
        self.frp_thread = None
        
        self.log_manager = LogManager()
        self.config_manager = ConfigManager()  # 初始化配置管理器
        
        self.init_ui()
        self.load_user_config()  # 加载用户配置
        self.check_files()
        self.check_ini_content()

    def init_ui(self):
        """初始化用户界面"""
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)  
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        status_layout = QHBoxLayout()
        status_label = QLabel("连接状态:")
        status_label.setFont(QFont("Microsoft YaHei UI", 10))
        self.status_value = QLabel("离线")
        self.status_value.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
        self.status_value.setStyleSheet("color: red;")
        status_layout.addWidget(status_label)
        status_layout.addWidget(self.status_value)
        status_layout.addStretch()
        main_layout.addLayout(status_layout)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)
        
        config_group = QWidget()
        config_layout = QVBoxLayout(config_group)
        config_layout.setSpacing(10)
        
        name_layout = QHBoxLayout()
        name_label = QLabel("连接名称:")
        name_label.setFont(QFont("Microsoft YaHei UI", 9))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("请输入连接名称,尽可能使用数字和字母结合，使用其他字符可能导致显示错误")
        self.name_input.setFont(QFont("Microsoft YaHei UI", 9))
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        config_layout.addLayout(name_layout)
        
        local_port_layout = QHBoxLayout()
        local_port_label = QLabel("本地端口:")
        local_port_label.setFont(QFont("Microsoft YaHei UI", 9))
        self.local_port_input = QLineEdit()
        self.local_port_input.setPlaceholderText("请输入本地端口,输入0-65535之间的数字")
        self.local_port_input.setFont(QFont("Microsoft YaHei UI", 9))
        local_port_layout.addWidget(local_port_label)
        local_port_layout.addWidget(self.local_port_input)
        config_layout.addLayout(local_port_layout)
        
        remote_port_layout = QHBoxLayout()
        remote_port_label = QLabel("远程端口:")
        remote_port_label.setFont(QFont("Microsoft YaHei UI", 9))
        self.remote_port_input = QLineEdit()
        self.remote_port_input.setPlaceholderText("请输入远程端口,也就是连接时的端口")
        self.remote_port_input.setFont(QFont("Microsoft YaHei UI", 9))
        remote_port_layout.addWidget(remote_port_label)
        remote_port_layout.addWidget(self.remote_port_input)
        config_layout.addLayout(remote_port_layout)
        #自定义联系方式↓还有你开放给用户的端口什么什么的
        port_hint = QLabel("目前开放端口：(设置为你的端口)，如需使用其他端口（或端口已被使用）请联系<a href='你的联系方式地址' style='color:#DE5330;text-decoration:underline;'>你的联系方式名称（昵称）</a>")
        port_hint.setFont(QFont("Microsoft YaHei UI", 9))
        port_hint.setTextFormat(Qt.RichText)
        port_hint.setTextInteractionFlags(Qt.TextBrowserInteraction)
        port_hint.setOpenExternalLinks(True)
        config_layout.addWidget(port_hint)
        
        main_layout.addWidget(config_group)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)
        
        log_label = QLabel("日志信息:")
        log_label.setFont(QFont("Microsoft YaHei UI", 10))
        main_layout.addWidget(log_label)
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont("Consolas", 9))
        self.log_area.setMinimumHeight(200)  
        
        self.log_area.setAcceptRichText(True)
        main_layout.addWidget(self.log_area)
        
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("启动")
        self.start_button.setFont(QFont("Microsoft YaHei UI", 10))
        self.start_button.setMinimumHeight(35)
        self.start_button.clicked.connect(self.start_frp)
        
        self.stop_button = QPushButton("退出")
        self.stop_button.setFont(QFont("Microsoft YaHei UI", 10))
        self.stop_button.setMinimumHeight(35)
        self.stop_button.clicked.connect(self.stop_frp)
        self.stop_button.setEnabled(False)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        main_layout.addLayout(button_layout)
        
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
    
    def check_files(self):
        """检查必要的文件是否存在，并显示带URL链接的自定义提示"""
        frpc_missing = not os.path.exists(self.frpc_path)
        config_missing = not os.path.exists(self.config_path)
    
        if frpc_missing or config_missing:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("找不到文件啦！")
        
           
            message = ""
            if config_missing:#自定义找不到ini文件时候的提示
                message += """
<p>我没有找到 <strong>frpc.ini</strong> ！！！</p>
<p>这是内网穿透的配置文件，工具得有这个文件才能正常工作。</p>
<p>如果这是你第一次使用，找TA：</p>
<p>QQ<a href="你的联系方式地址" style="color:#fe7676">你的联系方式名称</a></p>
<p>或使用邮箱找<a href="mailto:邮箱地址" style="color:#fe7676">你的邮箱</a></p>
<p><strong>该程序仅供<span style="color:#fe7676">你的名字</span>的内网穿透使用，擅自修改ini文件无法使用该工具连接。</strong></p>
"""
                if frpc_missing:
                    message += "<hr>"
        
            if frpc_missing:
                message += """
            <p>未找到 <strong>frpc.exe</strong> 文件</p>
            <p>这是内网穿透的核心程序，程序需要此文件才能正常工作。</p>
            <p>请重新下载完整的应用，仅解压，且不要修改其中的任何内容！</p>
            """
        
            msg_box.setText(message)
            msg_box.setTextFormat(Qt.RichText)
        
            # 获取消息框中的QLabel并设置链接处理
            for child in msg_box.children():
                if isinstance(child, QLabel):
                    if child.text() == message:
                        child.setOpenExternalLinks(True)
                        break
        
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
            msg_box.exec_()
        
            self.start_button.setEnabled(False)

    def check_ini_content(self):
        """检查ini文件内容是否包含特定符号，或是否能正常读取"""
        if os.path.exists(self.config_path):
            try:
                # 尝试使用UTF-8读取文件
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # 处理编码错误
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("ini文件损坏")
                msg_box.setText("ini文件格式错误或已损坏，\n删除ini文件并重启工具以重新获取。")
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.setIcon(QMessageBox.Critical)
                msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
                msg_box.exec_()
                sys.exit(1)
            except Exception as e:
                # 处理其他读取错误
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("ini文件错误")
                msg_box.setText(f"无法读取ini文件: {str(e)}\n删除ini文件并重启工具以重新获取。")
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.setIcon(QMessageBox.Critical)
                msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
                msg_box.exec_()
                sys.exit(1)
                
            if '[自定义符号]' not in content:# 检查ini文件内容是否包含特定符号，这里设置为'[自定义符号]'推荐设置为常见编辑器不可见的符号
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("ini文件被修改")
                msg_box.setText("ini文件内容不完整，请删除ini文件并重启工具以重新获取。")
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.setIcon(QMessageBox.Critical)
                msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
                msg_box.exec_()
                sys.exit(1)

    def update_config(self):
        """更新配置文件内容"""
        name = self.name_input.text().strip()
        local_port = self.local_port_input.text().strip()
        remote_port = self.remote_port_input.text().strip()

        if not name or not local_port or not remote_port:
            QMessageBox.warning(self, "输入错误", "请填写连接名称、本地端口和远程端口。")
            return False

        try:
            local_port = int(local_port)
            remote_port = int(remote_port)
            if not (0 <= local_port <= 65535) or not (0 <= remote_port <= 65535):
                QMessageBox.warning(self, "输入错误", "本地端口和远程端口必须在0-65535之间。")
                return False
        except ValueError:
            QMessageBox.warning(self, "输入错误", "本地端口和远程端口必须是有效的整数。")
            return False

        config = configparser.ConfigParser()
        config['common'] = {
            'server_addr': 'your_server_address',#将your_server_address替换为你的服务器地址
            'server_port': '7000',#将7000替换为你的服务器的frp监听端口
            'token': ''#将引号内替换为你的服务器的token
        }
        config[name] = {
            'type': 'tcp',
            'local_ip': '127.0.0.1',
            'local_port': local_port,
            'remote_port': remote_port
        }

        try:
            with open(self.config_path, 'w', encoding='utf-8') as configfile:
                config.write(configfile)
            return True
        except Exception as e:
            QMessageBox.critical(self, "配置文件写入错误", f"写入配置文件时出现错误: {str(e)}")
            return False

    def on_process_finished(self):
        """FRP进程结束时的处理"""
        log_msg = "FRP连接已停止"
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.update_log(log_msg)

        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                f.write("感谢您的使用~[自定义符号]")
        except Exception as e:
            print(f"修改文件内容失败: {e}")

    def closeEvent(self, event):
        """窗口关闭时的处理"""
        if self.frp_thread and self.frp_thread.running:
            reply = QMessageBox.question(
                self, 
                '确认退出', 
                'FRP连接正在运行，是否要停止连接并退出?',
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                log_msg = "用户请求关闭应用程序，正在停止FRP连接..."
                self.log_area.append(f"<span style='color:blue;'>{log_msg}</span>")
                self.log_manager.write_app_log(log_msg)
                
                self.stop_frp()
                self.frp_thread.wait()
                
                self.save_user_config()  # 保存用户配置
                self.log_manager.close()
                event.accept()
            else:
                event.ignore()
        else:
            self.save_user_config()  # 保存用户配置
            self.log_manager.close()
            event.accept()

    def load_user_config(self):
        """加载用户配置"""
        config = self.config_manager.load_config()
        self.name_input.setText(config['name'])
        self.local_port_input.setText(config['local_port'])
        self.remote_port_input.setText(config['remote_port'])
    
    def save_user_config(self):
        """保存用户配置"""
        name = self.name_input.text()
        local_port = self.local_port_input.text()
        remote_port = self.remote_port_input.text()
        self.config_manager.save_config(name, local_port, remote_port)

    def start_frp(self):
        """启动FRP连接"""
        if self.frp_thread and self.frp_thread.running:
            return

        if not self.update_config():
            return

        try:
            os.system(f'attrib +h {self.config_path}')
        except Exception as e:
            print(f"隐藏文件失败: {e}")
        try:
            os.system(f'attrib -h {self.config_path}')
        except Exception as e:
            print(f"取消隐藏文件失败: {e}")

        self.frp_thread = FRPThread(self.frpc_path, self.config_path, self.log_manager)
        self.frp_thread.status_updated.connect(self.update_status)
        self.frp_thread.log_updated.connect(self.update_log)
        self.frp_thread.process_finished.connect(self.on_process_finished)

        self.frp_thread.proxy_started.connect(self.on_proxy_started)
        self.frp_thread.start()

        log_msg = "正在启动FRP连接..."
        self.log_area.append(f"<span style='color:blue;'>{log_msg}</span>")
        self.log_manager.write_app_log(log_msg)

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def stop_frp(self):
        """停止FRP连接"""
        if self.frp_thread and self.frp_thread.running:
            log_msg = "正在停止FRP连接..."
            self.log_area.append(f"<span style='color:blue;'>{log_msg}</span>")
            self.log_manager.write_app_log(log_msg)
            self.frp_thread.stop()

    def update_status(self, status):
        """更新连接状态显示"""
        self.status_value.setText(status)
        if status == "在线":
            self.status_value.setStyleSheet("color: green;")
        else:
            self.status_value.setStyleSheet("color: red;")

    def update_log(self, log):
        """更新日志显示"""
        color = "blue"
        if "[错误]" in log or "错误" in log:
            color = "red"
        elif "[警告]" in log or "警告" in log:
            color = "#D28C00"
        elif "[信息]" in log or "成功" in log or "已启动" in log:
            color = "green"

        self.log_area.append(f"<span style='color:{color};'>{log}</span>")
        cursor = self.log_area.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_area.setTextCursor(cursor)

    def on_proxy_started(self, remote_port):
        """代理启动成功后的处理"""
        server_address = self.get_server_address_from_config()
        
        if server_address:
            current_time = datetime.now().strftime("%H:%M:%S")
            log_msg = f"[{current_time}][信息]链接地址为：{server_address}:{remote_port}。"
            self.log_area.append(f"<span style='color:blue;'>{log_msg}</span>")
            self.log_manager.write_app_log(log_msg)
            log_msg2 = f"[{current_time}][警告]即便显示成功，也要确保已经和服务器管理员确定开放了端口！"
            self.log_area.append(f"<span style='color:red;'>{log_msg2}</span>")
            self.log_manager.write_app_log(log_msg2)
            log_msg3 = f"[{current_time}][那什么]工具由糯米茨开发，欢迎来找我玩！QQ：1090007836"
            '''请勿删除该行消息'''
            self.log_area.append(f"<span style='color:red;'>{log_msg3}</span>")
            self.log_manager.write_app_log(log_msg3)
        else:
            self.update_log("[错误]无法从配置文件中获取服务器地址")

    def get_server_address_from_config(self):
        """从配置文件读取服务器地址"""
        try:
            config = configparser.ConfigParser()
            config.read(self.config_path, encoding='utf-8')
            if 'common' in config and 'server_addr' in config['common']:
                return config['common']['server_addr']
            else:
                self.update_log("[警告]配置文件中未找到服务器地址")
                return None
        except Exception as e:
            self.update_log(f"[错误]读取配置文件失败: {e}")
            return None

if __name__ == "__main__":
    # 创建单实例控制器
    single_instance = SingleInstance()
    
    # 尝试获取应用锁
    if not single_instance.acquire_lock():
        # 如果获取锁失败，说明已有实例在运行
        QMessageBox.critical(None, "应用已在运行", "糯米茨内网穿透工具已经在运行中，不能同时打开多个实例。")
        sys.exit(1)
    
    app = QApplication(sys.argv)

    font = QFont("Microsoft YaHei UI")
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
