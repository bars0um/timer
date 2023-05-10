Python Timer Lite

This relatively light script allows you to run a simple command line timer to log time against a certain task.

Properties file should be updated with a system where you have ssh access (you should use a key to authenticate) and the folder where the timesheet is saved. Ensure you enable remote_save if you want this option.

```
host=timer # name of host from your ssh/config
path=~/timer/ # folder where you want the timesheet csv saved
remote_save=true # whether you want to save the file remotely
```
