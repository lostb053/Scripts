## #move.bat
Move contents from multiple folders in a directory to the same directory.

Before
```
Dir1/
  Dir2/
    F1
  Dir3/
    F2
  Dir4/
    F3
    F4
    F5
```
After
```
Dir1/
  Dir2/
  Dir3/
  Dir4/
  F1
  F2
  F3
  F4
  F5
```

## arr.bat
just a single click arr startup. can be added as startup program

## clist.py
designed to compare simkl lists with shows/movies added in sonarr/radarr

## sss.py
designed to complement clist.py and add the shows to your radarr, sonarr instances

> **why use this when import lists exists?**
>
> cuz this script can be scheduled to increase sync frequency instead of 6 hrs waiting period.
> but that isn't what this script is for. it can also lookup titles and add the best match to your library (not always accurate)


## monitor.ps1
monitors usage of private bytes and gives a prompt should the bytes exceed certain threshold, a very basic memory leak detector. takes arguments
```
    --ThresholdGB = 3,
    --CheckIntervalSeconds = 30,
    --RunOnce
```

## pwsh_nw.vbs
just a wrapper so scheduling the memory leak detector doesn't pop up a console window every time it executes
