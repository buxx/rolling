@echo off

:: see https://github.com/vegardit/cygwin-portable-installer/blob/master/cygwin-portable-installer.cmd for original authors*
:: SPDX-License-Identifier: Apache-2.0

set DOWNLOADER=%INSTALL_ROOT%downloader.vbs
set CYGWIN_MIRROR=http://linux.rz.ruhr-uni-bochum.de/download/cygwin
set CYGWIN_ARCH=auto
set CYGWIN_USERNAME=root
set CYGWIN_PACKAGES=python37,wget,zip,python37-pip,gcc-g++,make,python37-devel,zlib,zlib-devel,libjpeg8,libjpeg-devel
set MINTTY_OPTIONS=--Title Rolling ^
  -o Columns=160 ^
  -o Rows=50 ^
  -o BellType=0 ^
  -o ClicksPlaceCursor=yes ^
  -o CursorBlinks=yes ^
  -o CursorColour=96,96,255 ^
  -o CursorType=Block ^
  -o CopyOnSelect=yes ^
  -o RightClickAction=Paste ^
  -o Font="Courier New" ^
  -o FontHeight=10 ^
  -o FontSmoothing=None ^
  -o ScrollbackLines=10000 ^
  -o Transparency=off ^
  -o Term=xterm-256color ^
  -o Charset=UTF-8 ^
-o Locale=C

echo Installing Cygwin

set INSTALL_ROOT=%~dp0
set CYGWIN_ROOT=%INSTALL_ROOT%cygwin
echo Creating Cygwin root [%CYGWIN_ROOT%]...
if not exist "%CYGWIN_ROOT%" (
    md "%CYGWIN_ROOT%" || goto :fail
)

:: https://blogs.msdn.microsoft.com/david.wang/2006/03/27/howto-detect-process-bitness/
if "%CYGWIN_ARCH%" == "auto" (
    if "%PROCESSOR_ARCHITECTURE%" == "x86" (
        if defined PROCESSOR_ARCHITEW6432 (
            set CYGWIN_ARCH=64
        ) else (
            set CYGWIN_ARCH=32
        )
    ) else (
        set CYGWIN_ARCH=64
    )
)

:: download Cygwin 32 or 64 setup exe depending on detected architecture
if "%CYGWIN_ARCH%" == "64" (
    set CYGWIN_SETUP=setup-x86_64.exe
) else (
    set CYGWIN_SETUP=setup-x86.exe
)

if exist "%CYGWIN_ROOT%\%CYGWIN_SETUP%" (
    del "%CYGWIN_ROOT%\%CYGWIN_SETUP%" || goto :fail
)

wget%CYGWIN_ARCH% https://cygwin.org/%CYGWIN_SETUP% -O "%CYGWIN_ROOT%\%CYGWIN_SETUP%" || goto :fail

echo Running Cygwin setup...
"%CYGWIN_ROOT%\%CYGWIN_SETUP%" --no-admin ^
 --site %CYGWIN_MIRROR% %CYGWIN_PROXY% ^
 --root "%CYGWIN_ROOT%" ^
 --local-package-dir "%CYGWIN_ROOT%\.pkg-cache" ^
 --no-shortcuts ^
 --no-desktop ^
 --delete-orphans ^
 --upgrade-also ^
 --no-replaceonreboot ^
 --quiet-mode ^
 --packages dos2unix,wget,%CYGWIN_PACKAGES% || goto :fail

echo Install rolling scripts

copy init.sh cygwin\bin\init.sh || goto :fail
copy install_rolling.sh cygwin\bin\install_rolling.sh || goto :fail
copy update_rolling.sh cygwin\bin\update_rolling.sh || goto :fail
copy start_rolling_tui.sh cygwin\bin\start_rolling_tui.sh || goto :fail

echo Install Rolling
cygwin\bin\bash --login -i -c "/bin/init.sh && /bin/install_rolling.sh" || goto :fail

echo Delete install scripts

del init.sh
del install_rolling.sh
del update_rolling.sh
del start_rolling_tui.sh
del install.cmd
del wget32.exe
del wget64.exe

echo Install finished
timeout /T 30
