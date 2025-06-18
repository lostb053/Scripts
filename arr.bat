@echo off
START /D "C:\Program Files\SABnzbd" SABnzbd.exe
START /D "C:\ProgramData\Sonarr\bin" Sonarr.exe
START /D "C:\ProgramData\Radarr\bin" Radarr.exe
START /D "C:\ProgramData\Prowlarr\bin" Prowlarr.exe
exit
