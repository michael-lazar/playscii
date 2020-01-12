@echo off

set BUILD_EXE_PATH=dist\playscii.exe
set OUTPUT_DIR=dist\playscii\
set ICON_PATH=ui\playscii.ico
set XCOPY_INCLUDE=win_xcopy_include
set XCOPY_EXCLUDE=win_xcopy_exclude
set COPY_INCLUDE=win_copy_include

echo Creating new build...

REM ==== include pdoc/mako templates from python site-packages - annoying!
python -c "from site import getsitepackages; print(getsitepackages()[1])" > pypath
set /p PYPATHSP=<pypath
del pypath
mkdir %OUTPUT_DIR%pdoc\templates\

REM ==== -F = everything in one file; -w = no console window; -i = path to icon
pyinstaller -F -w -i %ICON_PATH% --add-data %PYPATHSP%\pdoc\templates\*.mako;pdoc\templates\ playscii.py
echo Build done!

REM ==== move build so that ZIP will have a subdir enclosing everything
mkdir %OUTPUT_DIR%
move %BUILD_EXE_PATH% %OUTPUT_DIR%

echo -----------

echo Copying external files...
REM ==== xcopy dirs recursively
for /f "tokens=*" %%i in (%XCOPY_INCLUDE%) DO (
echo %%i
xcopy /E/Y "%%i" "%OUTPUT_DIR%\%%i" /exclude:%XCOPY_EXCLUDE%
)
REM ==== regular copy files (non-recursively)
for /f "tokens=*" %%i in (%COPY_INCLUDE%) DO (
echo %%i
copy /Y "%%i" %OUTPUT_DIR% > NUL
)

echo -----------
echo Done!

pause
