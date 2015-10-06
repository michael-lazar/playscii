@echo off
set ZIP_EXE="c:\Program Files\7-Zip\7z.exe"
REM get version number from file
set /p PLAYSCII_VERSION=<version
cd dist
del /Q playscii_win32*.zip
REM name zip according to version
%ZIP_EXE% a -r playscii_win32-%PLAYSCII_VERSION%.zip ./*
move playscii_win32-%PLAYSCII_VERSION%.zip ..\
cd ..