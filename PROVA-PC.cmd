@echo off
rem EnterElectro-Recomp - prova del PC: il gioco va a piena velocita' su questo computer? (tools\prova_pc.py)
rem Prima aggiungi almeno un disco con SM2-Launcher. La prova, se serve, installa quella versione con il PGO e con
rem l'eseguibile di prova (sui PC lenti anche piu' di mezz'ora, una volta sola), apre il gioco una volta per circa 3
rem minuti (audio spento: non toccare la sua finestra) e scrive work\prova_pc\rapporto.txt e uno zip da mandare.
rem Opzioni: --profilo <VERSIONE>, --senza-installare, --secondi-cpu N, --cpu tutti^|meta, --lingua it^|en.
rem
rem English: EnterElectro-Recomp PC test - does the game run at full speed on this computer? (tools\prova_pc.py)
rem First add at least one disc with SM2-Launcher. If needed, the test installs that version with PGO and with the
rem test executable (on slow PCs even more than half an hour, only once), opens the game once for about 3 minutes
rem (audio off: do not touch its window) and writes work\prova_pc\rapporto.txt and a zip to send.
rem Options: --profile <VERSION>, --no-install, --cpu-seconds N, --cpu all^|half, --language it^|en.
setlocal
cd /d "%~dp0"
call "%~dp0SM2-Launcher.cmd" stato
if not exist "tools\toolchain\cmake-clang-v1\env.bat" (
  echo ERRORE: gli strumenti di compilazione non ci sono ^(vedi i messaggi qui sopra^)
  echo ERROR: the build tools are missing ^(see the messages above^)
  goto :fine
)
call "tools\toolchain\cmake-clang-v1\env.bat"
python tools\prova_pc.py %*
:fine
if "%~1"=="" pause
