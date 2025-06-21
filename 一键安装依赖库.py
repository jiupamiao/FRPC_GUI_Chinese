import subprocess
import sys
import importlib.util
import platform

def check_dependency(dep_name):
    """检查依赖库是否已安装"""
    spec = importlib.util.find_spec(dep_name)
    return spec is not None

def install_dependencies():
    """安装所需的依赖库"""
    dependencies = ['pyyaml', 'PyQt5', 'pyinstaller', 'tqdm']
    missing_deps = [dep for dep in dependencies if not check_dependency(dep)]
    
    if not missing_deps:
        print("所有依赖库已安装")
        return True
    
    print(f"需要安装以下依赖库: {', '.join(missing_deps)}")
    
    try:
        # 使用subprocess调用pip安装缺失的依赖库
        for dep in missing_deps:
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
            print(f"{dep} 安装成功")
        
        print("安装完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"安装失败: {e}")
        print(f"安装失败，请尝试手动安装: {', '.join(missing_deps)}")
        return False

def wait_for_keypress():
    """等待用户按键"""
    print("按任意键退出...")
    try:
        if platform.system() == "Windows":
            import msvcrt
            msvcrt.getch()
        else:
            # Linux/macOS
            import termios
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                new = termios.tcgetattr(fd)
                new[3] = new[3] & ~termios.ICANON & ~termios.ECHO
                termios.tcsetattr(fd, termios.TCSANOW, new)
                sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSANOW, old)
    except Exception as e:
        # 备用方案：直接等待输入
        input("\n按回车键退出...")

if __name__ == "__main__":
    install_dependencies()
    wait_for_keypress()