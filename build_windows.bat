@echo off

echo Creating new build...
pyinstaller --icon=ui\playscii.ico playscii_win.spec

echo Done!
pause
