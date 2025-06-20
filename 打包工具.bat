
pip install pyinstaller
if errorlevel 1 (
    echo error: Install pyinstaller failed!
    goto :END
)

pip install PyQt5
if errorlevel 1 (
    echo error: Install PyQt5 failed!
    goto :END
)


pyinstaller --onefile --name Tool_FRP_Non-official --icon=icon.ico app.pyw
if errorlevel 1 (
    echo error: Build failed!
    goto :END
)

