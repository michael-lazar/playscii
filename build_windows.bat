@echo off

echo Creating new build...
REM ==== -F = everything in one file; -w = no console window; -i = path to icon
pyinstaller -F -w -i ui\playscii.ico playscii.py
echo Build done!

REM ==== move build so that ZIP will have a subdir enclosing everything
mkdir dist\playscii
move dist\playscii.exe dist\playscii\

echo -----------

echo Copying external files...
REM ==== xcopy dirs recursively
for /f "tokens=*" %%i in (win_xcopy_include) DO (
echo %%i
xcopy /E/Y "%%i" "dist\playscii\%%i" /exclude:win_copy_exclude
)
REM ==== regular copy files (non-recursively)
for /f "tokens=*" %%i in (win_copy_include) DO (
echo %%i
copy /Y "%%i" "dist\playscii\" > NUL
)

echo -----------
echo Done!

pause
