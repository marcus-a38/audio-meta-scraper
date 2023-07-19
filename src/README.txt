==========================================================================================
                                        INFO
==========================================================================================

Author: Marcus Antonelli
E-Mail: marcus.an38@gmail.com

This project was written for my dad. He wanted to grab all of the metadata from songs in his
music collection, and store them in a DB for a more structured data format.

Contents of this folder were written on Windows 11 using Python version 3.9.13

Much of this code has not been written or debugged for UNIX or Mac operating systems,
though I will eventually work on cross-OS support.

==========================================================================================
                                     DISCLAIMER
==========================================================================================
This code is not packaged or production ready. While the code does operate with intended
behavior on its original environment, there is no guarantee that this is true for any other
machine; borrow and execute any of the source code with caution. I, the author, am not
liable for any damages caused through the use of this program. There is NO WARRANTY. Lastly,
you acknowledge- through use and modification of this program- that none of the materials
or original source code found in this repository are to be used commercially unless given
permission by me, the author (Marcus Antonelli).
==========================================================================================

This folder's structure:

metaflac.py
|
|---------->  Command-Line Utility to search for FLAC files and store their metadata in a DB
|
background.py
|
|-----------> Small script that uses `metaflac` funcs to store the metadata of all FLACs on PC
|
scheduler.py
|
|-----------> A one-time-use script that uses PS to create a scheduled task (running background.py)

==========================================================================================

Working with the scheduler:

The scheduler script makes changes to your PC's scheduled task list, accessing more priveleged
contents of your PC. Because of this, you must make sure to run it as an Administrator.

Further, the script does not offer a feature to remove the scheduled task. That functionality
could be useful or necessary in some situations, so until I implement it in the script, here's 
two simple steps to remove the task, if needed:

1. Open/run Command Prompt as an Administrator
2. Type in: schtasks /DELETE /TN "searchForFlac"

==========================================================================================

If you have any questions, concerns, or want to report a bug, please do so at:

GitHub --> https://github.com/marcus-a38/flacscript
E-Mail --> marcus.an38@gmail.com

Enjoy!
