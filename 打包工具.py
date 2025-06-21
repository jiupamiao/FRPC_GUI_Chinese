import os
import subprocess
import shutil
import sys
import time
from tqdm import tqdm
from pathlib import Path

def check_icon():
    """检查图标文件是否存在，并询问用户是否继续"""
    if os.path.exists("icon.ico"):
        return True
    
    print("图标文件不存在，要继续吗？(y/n)")
    while True:
        choice = input().strip().lower()
        if choice == 'y':
            print("继续打包过程（不使用图标）...")
            return False
        elif choice == 'n':
            print("用户取消，脚本退出")
            sys.exit(0)
        else:
            print("无效输入，请输入y或n")

def run_pyinstaller(use_icon=True):
    """运行PyInstaller打包应用程序"""
    print("开始打包应用程序...")
    
    # 构建PyInstaller命令
    cmd = ["pyinstaller", "--onefile", "--name", "Tool_FRP_Non-official"]
    
    if use_icon:
        cmd.extend(["--icon=icon.ico"])
    
    cmd.append("app.pyw")
    
    # 执行PyInstaller命令
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )
    
    # 使用tqdm显示进度条（简化版）
    print("PyInstaller正在处理,请耐心等待...")
    for line in iter(process.stdout.read, ''):
        print(line, end='')
    
    process.wait()
    
    if process.returncode != 0:
        print(f"错误：PyInstaller打包失败，返回代码：{process.returncode}")
        return False
    
    print("PyInstaller打包完成")
    return True

def create_distribution_folder():
    """创建分发文件夹并整理文件"""
    print("开始整理分发文件...")
    
    # 创建目标文件夹
    dist_folder = "内网穿透工具"
    os.makedirs(dist_folder, exist_ok=True)
    
    # 需要复制的文件列表
    files_to_copy = [
        "dist/Tool_FRP_Non-official.exe",  # PyInstaller生成的exe文件
        "frpc.exe",
        "frpc.ini",
        "icon.ico",
        "frp-LICENSE",
        "NOTICE"
    ]
    
    # 复制文件并显示进度条
    for file_path in tqdm(files_to_copy, desc="复制文件"):
        if os.path.exists(file_path):
            try:
                shutil.copy2(file_path, dist_folder)
            except Exception as e:
                print(f"错误：无法复制文件 {file_path}: {e}")
                return False
        else:
            print(f"警告：文件 {file_path} 不存在，跳过")
    
    print("文件整理完成")
    return True

def wait_for_keypress():
    """等待用户按键"""
    print("按任意键退出...")
    try:
        if os.name == "nt":  # Windows
            import msvcrt
            msvcrt.getch()
    except:
        input()  # 备用方案

def main():
    """主函数，控制整个打包和整理流程"""
    print("=== 内网穿透工具打包脚本 ===")
    
    # 检查必要的依赖
    try:
        import tqdm
    except ImportError:
        print("错误：缺少tqdm库，请先运行依赖安装脚本")
        sys.exit(1)
    
    # 检查PyInstaller是否安装
    try:
        subprocess.run(["pyinstaller", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("错误：未找到PyInstaller，请先运行依赖安装脚本")
        sys.exit(1)
    
    # 检查图标文件
    use_icon = check_icon()
    
    # 运行PyInstaller打包
    if not run_pyinstaller(use_icon):
        print("打包过程中出现错误，脚本终止")
        sys.exit(1)
    
    # 创建分发文件夹
    if not create_distribution_folder():
        print("文件整理过程中出现错误，脚本终止")
        sys.exit(1)
    
    # 显示完成信息
    print("\n=== 打包完成 ===")
    print("将文件夹\"内网穿透工具\"中的文件压缩即可分发")
    
    wait_for_keypress()

if __name__ == "__main__":
    main()