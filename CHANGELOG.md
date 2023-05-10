10-05-2023 - version 0.1
========== 

- added support for ssh storage of the timesheet.csv this allows you to store the timesheet remotely and use script from any system as long as you have a remote system you can ssh to. Ensure that your ssh/config file has an entry that facilitates key access to make this smooth.
- added logging
- download is made again before upload when stopping the timer to ensure we are using the latest timesheet when recording time



