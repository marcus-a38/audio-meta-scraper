##################################################################################
#================================================================================#
# Author: Marcus Antonelli | GitHub: /marcus-a38 | E-Mail: marcus.an38@gmail.com #
#================================================================================#
#                Most Recent Publish Date: 7/19/2023 (version 1)                 #
#================================================================================#
#                                                                                #
#                              -- DISCLAIMER --                                  #
#                                                                                #
#     You may not use this script commercially without the author's consent      #
#         All changes made to the original content of this script must be        #
#          documented in the open source material (non-commercial use.)          #
#     This script offers no warranty, nor does the author hold any liability     #
#     for issues that may be encountered or caused by the use of this script.    #
#                                                                                #
#================================================================================#
##################################################################################

import os
import subprocess

DIR = os.getcwd()

print("Welcome to the FLAC Scan Scheduler!\n")

# Check if the input is a legitimate 24-hour format time
def is_valid_time(time: str):
    split_time = time.split(":")

    if len(split_time[0]) != 2 or len(split_time[1]) != 2:
        return False

    # A number of checks: the split list must only have 2 elements, 
    # the hour slot musn't be less than 0 or greater than 23, and the 
    # minute slot musn't be less than 0 or greater than 59.
    try: 
        hour = int(split_time[0])
        min = int(split_time[1])
    except:
        return False
    
    if len(split_time) > 2 or hour not in range(0, 24) or min not in range(0, 60):
        return False
    return True

# Run the scheduler PS script
def call_psscript(py_path: str, time: str):

    try:
        command = f'schtasks /Create /SC DAILY /TN "searchForFlac" /TR "python.exe {py_path}" /ST {time} /RU "SYSTEM"'
        subprocess.run(command, shell=True)
    except subprocess.CalledProcessError as err:
       print("Error creating scheduled task... More info: %s" % err)

# Grab desired user input for timed script execution
def get_time():
    while True:
        time_schedule = input("Input your desired time using the 24-hour time format (HH:MM) > ")
        if is_valid_time(time_schedule):
            return time_schedule
        else:
            os.system('cls')
            print("Invalid time, please try again.\n")

# Entry function
def main():
    py_script = os.path.join(DIR, "src", "background.py")
    exec_time = get_time()
    call_psscript(py_path=py_script, time=exec_time)
