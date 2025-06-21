pyinstaller --onefile --name Tool_FRP_Non-official --icon=icon.ico app.pyw
if errorlevel 1 (
    echo error: Build failed!
    goto :END
)

