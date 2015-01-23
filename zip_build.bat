@echo off
set ZIP_EXE="c:\Program Files\7-Zip\7z.exe"
del build.zip
REM ignore pycache dirs
dir /s/b dist\*__pycache__ > cachedirs
REM rename dist\ dir to the top level dir we want in the archive
move dist playscii
%ZIP_EXE% a -r playscii_build.zip playscii/*.* -x@cachedirs
REM put everything back
move playscii dist
del cachedirs
