@echo off

REM Playscii windows EXE build batch

REM Build needs to know where your python and SDL2 dll are, modify
REM the two lines below as needed:
set PYTHONPATH="c:\Python34"
set SDLPATH=".\"

echo Removing old build...
rmdir /S /Q dist\
mkdir dist

echo Creating new build...
python setup.py py2exe

echo Copying PyOpenGL libs to build dir...
mkdir dist\OpenGL
xcopy /e /v /Q "%PYTHONPATH%\Lib\site-packages\OpenGL\*.*" dist\OpenGL\
del /s /Q dist\OpenGL\*.pyc
del /s /Q dist\OpenGL\*.pyo

echo Copying SDL2.dll...
copy %SDLPATH%\SDL2.dll dist\

echo Copying Playscii data files...
mkdir dist\art
copy /v art\*.* dist\art\
mkdir dist\charsets
copy /v charsets\*.* dist\charsets\
mkdir dist\docs
copy /v docs\*.* dist\docs\
mkdir dist\palettes
copy /v palettes\*.* dist\palettes\
mkdir dist\scripts
copy /v scripts\*.* dist\scripts\
mkdir dist\shaders
copy /v shaders\*.* dist\shaders\
REM test game content
mkdir dist\games
xcopy /s games\*.* dist\games\
REM ignore ui art source assets (eg .xcf)
mkdir dist\ui
copy /v ui\*.png dist\ui\
copy README.md dist\
copy license.txt dist\
copy code_of_conduct.txt dist\
copy playscii.cfg.default dist\
copy binds.cfg.default dist\
copy version dist\

echo Done!
pause
