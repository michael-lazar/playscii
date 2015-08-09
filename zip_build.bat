@echo off
set ZIP_EXE="c:\Program Files\7-Zip\7z.exe"
REM get version number from file
set /p PLAYSCII_VERSION=<version
del playscii_win32*.zip
REM ignore pycache dirs
dir /s/b dist\*__pycache__ > cachedirs
REM rename dist\ dir to the top level dir we want in the archive
move dist playscii
REM name zip according to version
%ZIP_EXE% a -r playscii_win32-%PLAYSCII_VERSION%.zip playscii/*.* -x@cachedirs
REM put everything back
move playscii dist
del cachedirs
