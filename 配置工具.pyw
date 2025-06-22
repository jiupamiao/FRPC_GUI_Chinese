import yaml
import re
import tkinter as tk
from tkinter import messagebox
# 更新了替换规则
def replace_placeholders(py_file_path, yaml_file_path):
    # 读取YAML文件
    with open(yaml_file_path, 'r', encoding='utf-8') as yaml_file:
        config = yaml.safe_load(yaml_file)

    # 读取Python文件
    with open(py_file_path, 'r', encoding='utf-8') as py_file:
        py_content = py_file.read()

    # 替换自定义符号
    custom_symbol = config.get('custom_symbol')
    if custom_symbol:
        pattern = r"(?<=root\['custom_symbol'\] = ')[^']*"
        py_content = re.sub(pattern, custom_symbol, py_content)
        py_content = re.sub(r'\[自定义符号\]', custom_symbol, py_content)

    # 替换服务器地址
    server_address = config.get('server_address')
    if server_address:
        pattern = r"(?<='server_addr': ')[^']*"
        py_content = re.sub(pattern, server_address, py_content)

    # 替换服务器端口
    server_port = config.get('server_port')
    if server_port:
        pattern = r"(?<='server_port': ')[^']*"
        py_content = re.sub(pattern, server_port, py_content)

    # 替换token
    token = config.get('token')
    if token:
        pattern = r"(?<='token': ')[^']*"
        py_content = re.sub(pattern, token, py_content)

    # 替换找不到ini文件的提示信息
    missing_ini_message = config.get('missing_ini_message')
    if missing_ini_message:
        pattern = r'(?<=if config_missing:#自定义找不到ini文件时候的提示\n                message \+= """\n)[\s\S]*?(?="""\n)'
        py_content = re.sub(pattern, missing_ini_message, py_content)

    # 替换联系方式提示信息
    contact_hint = config.get('contact_hint')
    if contact_hint:
        pattern = r'(?<=#自定义联系方式↓还有你开放给用户的端口什么什么的\n        port_hint = QLabel\(")[^"]*(?="\))'
        py_content = re.sub(pattern, contact_hint, py_content)

    type = config.get('type')
    if type:
        pattern = r"(?<='type': ')[^']*"
        py_content = re.sub(pattern, type, py_content)

    # 将修改后的内容写回Python文件
    with open(py_file_path, 'w', encoding='utf-8') as py_file:
        py_file.write(py_content)

    # 创建一个隐藏的主窗口
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口

    # 显示消息弹窗
    messagebox.showinfo("成功", "修改完成")

    # 确保窗口完全关闭
    root.destroy()

if __name__ == "__main__":
    py_file_path = 'app.pyw'
    yaml_file_path = '应用配置文件.yaml'
    replace_placeholders(py_file_path, yaml_file_path)
