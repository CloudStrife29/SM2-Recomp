@echo off
rem SM2-Recomp - launcher (prototipo): dal disco dell'utente al gioco per PC, tutto in locale.
rem Doppio clic: finestra del launcher. Oppure da una finestra dei comandi, nella cartella del progetto:
rem   SM2-Launcher.cmd riconosci                    riconosce i dischi in input\
rem   SM2-Launcher.cmd importa "<percorso>"         riconosce un dump e lo sposta in input\<PROFILO>\
rem   SM2-Launcher.cmd installa --profilo <P>       prepara e compila quella versione in giochi\<P>\
rem   SM2-Launcher.cmd avvia --profilo <P>          gioca (--risoluzione 1080p ecc.)
rem   SM2-Launcher.cmd stato                        versioni, dischi e installazioni
rem Messaggi in italiano o in inglese (dal 4/11/2026): li sceglie il launcher dalla lingua di Windows; --lingua it^|en
rem per cambiarla. Qui sotto i messaggi di questo file sono scritti in tutte e due le lingue.
rem La prima volta prepara il toolchain portatile (llvm-mingw, CMake, Ninja, Python) in tools\toolchain\:
rem sempre la versione 1.0.14 (launcher 0.11), controllata con il suo SHA-256. Il pacchetto completo (dal 3/11/2026)
rem contiene gia' lo zip (circa 200 MB) e lo estrae senza internet; se lo zip manca lo scarica.
rem Non installa niente nel sistema e non cambia il PATH o il registro di Windows: il toolchain vale
rem solo per questa finestra.
rem
rem English: SM2-Recomp launcher (prototype): from the user's own disc to the PC game, all on this computer.
rem Double-click: launcher window. Or from a command window, in the project folder (the Italian names work too):
rem   SM2-Launcher.cmd identify                     recognizes the discs in input\
rem   SM2-Launcher.cmd import "<path>"              recognizes a dump and moves it to input\<PROFILE>\
rem   SM2-Launcher.cmd install --profile <P>        prepares and builds that version in giochi\<P>\
rem   SM2-Launcher.cmd play --profile <P>           plays (--resolution 1080p etc.)
rem   SM2-Launcher.cmd status                       versions, discs and installations
rem Messages in Italian or English: the launcher chooses from the Windows display language; --language it^|en to
rem change it. The messages of this file are written below in both languages.
rem The first time it prepares the portable build tools (llvm-mingw, CMake, Ninja, Python) in tools\toolchain\:
rem always version 1.0.14 (launcher 0.11), checked with its SHA-256. The complete package already contains the zip
rem (about 200 MB) and extracts it without internet; if the zip is missing it downloads it. It installs nothing in
rem the system and does not change the Windows PATH or registry: the build tools are used only in this window.
setlocal
cd /d "%~dp0"
if not exist "psxrecomp\psxrecomp_cli.py" (
  echo Manca psxrecomp: per giocare scarica il pacchetto completo di SM2-Recomp dalla pagina Releases:
  echo https://github.com/CloudStrife29/SM2-Recomp/releases ^(il Download ZIP del pulsante Code e gli archivi Source code non bastano^).
  echo psxrecomp is missing: to play, download the complete SM2-Recomp package from the Releases page:
  echo https://github.com/CloudStrife29/SM2-Recomp/releases ^(Download ZIP from the Code button and the Source code archives are not enough^).
  goto :fine
)
set "TC=tools\toolchain"
set "TCDIR=%TC%\cmake-clang-v1"
set "TCZIP=%TC%\cmake-clang-v1-windows-x64.zip"
set "TCURL=https://github.com/RetroPortingToolKit/RetroPorting-Toolchains/releases/download/v1.0.14/cmake-clang-v1-windows-x64.zip"
set "TCSHA=28da9742385e7ff875b3d9311e8ed89dbdc84f27b6ecba2bc0d0acc11f6d2b4d"
set "SCARICATO="
if exist "%TCDIR%\env.bat" goto :pronto
if not exist "%TC%" mkdir "%TC%"
if exist "%TCZIP%" goto :dalpacchetto
echo Primo avvio: lo zip degli strumenti di compilazione non c'e' ^(il pacchetto completo lo contiene gia'^).
echo First start: the build tools zip is not here ^(the complete package already contains it^).
echo Lo scarico da internet ^(versione 1.0.14, circa 200 MB^)...
echo Downloading it from the internet ^(version 1.0.14, about 200 MB^)...
curl.exe -fL -o "%TCZIP%" "%TCURL%"
if errorlevel 1 (
  echo ERRORE: download del toolchain non riuscito.
  echo ERROR: the build tools download failed.
  echo Senza internet serve il pacchetto completo di SM2-Recomp, che contiene gia' %TCZIP%:
  echo in alternativa copia quel file in %TC%\ e rilancia.
  echo Without internet you need the complete SM2-Recomp package, which already contains %TCZIP%:
  echo otherwise copy that file into %TC%\ and start again.
  if exist "%TCZIP%" del "%TCZIP%"
  goto :fine
)
set "SCARICATO=1"
goto :controlla
:dalpacchetto
echo Primo avvio: preparo gli strumenti di compilazione dallo zip del pacchetto ^(versione 1.0.14, niente download^)...
echo First start: preparing the build tools from the package zip ^(version 1.0.14, no download^)...
:controlla
certutil -hashfile "%TCZIP%" SHA256 | findstr /i /c:"%TCSHA%" >nul
if errorlevel 1 (
  echo ERRORE: %TCZIP% non e' il toolchain atteso ^(versione 1.0.14, SHA-256 %TCSHA%^)
  echo ERROR: %TCZIP% is not the expected build tools zip ^(version 1.0.14, SHA-256 %TCSHA%^)
  if defined SCARICATO del "%TCZIP%"
  if not defined SCARICATO echo Rimettilo dal pacchetto completo, oppure cancellalo e rilancia con internet: verra' scaricato di nuovo.
  if not defined SCARICATO echo Put it back from the complete package, or delete it and start again with internet: it will be downloaded again.
  goto :fine
)
:estrai
echo Estraggo gli strumenti in %TCDIR%\ ^(circa un minuto^)...
echo Extracting the build tools into %TCDIR%\ ^(about a minute^)...
if not exist "%TCDIR%" mkdir "%TCDIR%"
tar.exe -xf "%TCZIP%" -C "%TCDIR%"
if errorlevel 1 (
  echo ERRORE: estrazione del toolchain non riuscita
  echo ERROR: extracting the build tools failed
  goto :fine
)
:pronto
call "%TCDIR%\env.bat"
python tools\sm2_launcher.py %*
:fine
if "%~1"=="" pause
