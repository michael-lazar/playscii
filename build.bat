@echo off

REM Playscii windows EXE build batch

REM Build needs to know where your dlls are, modify line below as needed:
set DLLPATH=".\"

echo Creating new build...
pyinstaller playscii.spec --icon-file=ui\playscii.ico

echo Copying DLLs...
copy %DLLPATH%\*.dll dist\playscii

echo Done!
pause
