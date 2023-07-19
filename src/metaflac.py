##################################################################################
#================================================================================#
# Author: Marcus Antonelli | GitHub: /marcus-a38 | E-Mail: marcus.an38@gmail.com #
#================================================================================#
#                Most Recent Publish Date: 7/19/2023 (version 1)                 #
#================================================================================#
#                                                                                #
#                              -- DISCLAIMER --                                  #
#                                                                                #
#     You may not use this script commercially without the author's consent.     #
#         All changes made to the original content of this script must be        #
#          documented in the open source material (non-commercial use.)          #
#     This script offers no warranty, nor does the author hold any liability     #
#     for issues that may be encountered or caused by the use of this script.    #
#                                                                                #
#================================================================================#
##################################################################################

import sqlite3
import os
import re
import subprocess
import threading
from mutagen.flac import FLAC
from time import sleep

# Needs reformatting and simplification !!!
# Needs logging for exceptions !!!
# 

cwd = os.getcwd()
db_path = os.path.join(cwd, "db", "flacdata.db")
backup_db_path = os.path.join(cwd, "db", "backup.sql")

# Loading animation
def loading(stop: threading.Event):
    animation = '|/-\\'
    i = 0
    try:
        while not stop.is_set(): # Run the animation until the thread is smoothly terminated
            print("\rSearching for .flac files %s" % animation[i], end="", flush=True)
            i = (i + 1) % len(animation)
            sleep(0.5)
    except:
        stop.set()

# Setting up the thread for loading animation
stop_thread_event = threading.Event()
loading_anim_thread = threading.Thread(target=loading, args=(stop_thread_event,))

# Recover SQLite database in event of corruption
def recover_db():

    os.remove(db_path)  # Delete the old database file

    if os.path.exists(backup_db_path):
        os.system('sqlite3 "%s" < "%s"' % (db_path, backup_db_path)) # Re-create it using the SQL backup

    return sqlite3.connect(database=db_path)

# Returns a simple tuple of an SQLite3 Connection and Cursor
def create_db():
    try:
        conn = sqlite3.connect(database=db_path)
    except:
        if 'conn' in locals() and conn:
            conn.close()
        conn = recover_db()

    db_cursor = conn.cursor()
    return (conn, db_cursor)

# Creates the necessary DB tables (if nonexistent)
def create_table(cursor: sqlite3.Cursor):

    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS flac_file (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT UNIQUE,
            track_title TEXT,
            artist_name TEXT,
            album_title TEXT,
            genre TEXT,
            date TEXT,
            length TEXT,
            comment TEXT
        )
        """
    )

# Insert a new file's metadata into the DB
def insert_data(cursor: sqlite3.Cursor, data: tuple):

    cursor.execute(
        """
        INSERT INTO flac_file (
            file_path, 
            track_title, 
            artist_name, 
            album_title, 
            genre, 
            date,
            length,
            comment
            )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(file_path) DO NOTHING;
        """, data
        )

# Creates a backup of the previous DB state using SQL
def create_backup_sql(conn: sqlite3.Connection):

    with open(backup_db_path, "w") as backup_db:

        for line in conn.iterdump():
            backup_db.write(line + '\n')

# Extracts the metadata from FLAC files using mutagen.flac.FLAC
def analyze_flac(flac_path: str, silent = False):

    try:
        metadata = FLAC(flac_path)
    except Exception as err:
        ("Malformed FLAC file, skipping... More details: %s" % err)

    # Convert metadata.info.length (FLAC duration) from seconds to HH:MM:SS
    def file_length():

        seconds = metadata.info.length % (24 * 3600)
        hours = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60
        return "%d:%02d:%02d" % (hours, minutes, seconds)

    try: 
        data= (
            flac_path,
            metadata.get("title", ["NULL"])[0],
            metadata.get("artist", ["NULL"])[0],
            metadata.get("album", ["NULL"])[0],
            metadata.get("genre", ["NULL"])[0],
            metadata.get("date", ["NULL"])[0],
            file_length(),
            metadata.get("comment", ["NULL"])[0]
        )
        return data
    
    except Exception as err:
        if not silent:
            print("Error processing file %s... Skipping. Error info: %s" % (flac_path, err))
        return "continue"

# Grabs a list of the logical drives on PC
def get_drives():

    drive_str = subprocess.check_output("fsutil fsinfo drives")
    drive_list = drive_str.decode().split()
    return drive_list[1:]

# Searches a directory and all of its subdirectories for FLAC files
def search_dir(path: str):

    hits = []

    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith('.flac'):
                hits.append(os.path.join(root, file))
    return hits

# Main function for a directory search - can either walk the tree or do an in-place search
def search(path: str):

    while True:

        search_children = input("Do you want to search the subdirectories in this directory? (y/n) > ")
        hits = []

        if search_children.lower() in ['y', 'yes']:
            stop_thread_event.clear()
            loading_anim_thread.start()

            try:
                hits = search_dir(path)
            except Exception as err:
                stop_thread_event.set()
                print("Error encountered: %s" % err)
                exit(0)

            stop_thread_event.set()
            loading_anim_thread.join()
            break
            
        elif search_children.lower() in ['n', 'no']:
            
            flac_files = os.listdir(path)
            hits = list(filter(check_ext, flac_files))
            hits = [os.path.join(path, hit) for hit in hits]
            break

        else:
            print("Invalid input, please try again.\n")

    return hits

# Main input function that grabs a directory and normalizes it.
def get_flac_directory():

    while True:
        flac_directory = input("Provide the file directory containing FLAC files > ")
        flac_directory = re.split('[\\/]', flac_directory)

        # Logical drives such as 'C:' don't automatically inherit the os.sep delimiter when joining, so
        # we must replace the ':' with ':/' or ':\' manually.
        flac_directory = os.path.join(*tuple(part for part in flac_directory)).replace(':', (":"+os.sep))

        if os.path.exists(flac_directory):
            break
        
        else:
            print("Invalid directory, please try again.\n")

    return flac_directory

# Filter function to check if a given file ends with .flac
def check_ext(ele: str):

    if ele.endswith('.flac'):
        return True
    else:
        return False
    
# Traverses the entire tree for each of the PC's logical drive
def search_whole_pc():

   
    flac_directories = get_drives()
    flac_files = []
            
    for directory in flac_directories:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.flac'):
                    flac_files.append(os.path.join(root, file))
    return flac_files

# Menu, option to print all detected FLAC files
def print_files_menu(flac_files):

    while True:

        do_print = input("\nPrint list? (y/n) > ")

        if do_print.lower() in ['y', 'yes']:
            print('\n'.join([str(num + 1) + '. ' + file for num, file in enumerate(flac_files)]).replace(r'\n', '\n'))
            break
        elif do_print.lower() in ['n', 'no']:
            print("Okay. Moving on to analysis...")
            break
        else:
            print("Invalid input. Please try again.\n")

# Menu, option to search either the entire PC or a directory.
# TO ADD: option to search just 1 logical drive at a time
def search_pc_or_directory():

    while True:

        whole_or_part = input("Enter '0' to search your whole PC, or '1' to provide a directory > ")

        if whole_or_part == '0':
            stop_thread_event.clear()
            loading_anim_thread.start()
          
            try:
                flac_files = search_whole_pc()
            except Exception as err:
                stop_thread_event.set()
                exit(err)
              
            stop_thread_event.set()
            loading_anim_thread.join()
          
            break

        elif whole_or_part == '1':
            flac_directory = get_flac_directory()
            flac_files = search(flac_directory)
            break
        else:
            print("Invalid choice, please try again.\n")

    print("\r%s" % (" " * 32), end="")
    print("\rDone.")
    return flac_files

# Menu to choose which of the discovered files will be searched for metadata
def analyze_files_menu(cursor: sqlite3.Cursor, flac_files: list):

    while True:

        selection = input("Enter '0' to analyze all files, or provide an index or list ([index1, index2, ...]) > ")
    
        # Analyze all of the files
        if selection == '0':
    
            for flac_file in flac_files:
                metadata = analyze_flac(flac_file)

                if metadata == 'continue':
                    continue
                else:
                    insert_data(cursor, metadata)
            break

        # The user wants to analyze a list or range of files
        if selection.startswith('[') and selection.endswith(']'):

            if '...' in selection:
                indeces = selection.lstrip("[").rstrip("]").split(' ')
            else:
                indeces = selection.replace(' ', '').lstrip("[").rstrip("]").split(',')

            # If user provides string like [1 ... 5], analyze files 1, 2, 3, 4, and 5.
            if len(indeces) == 3 and indeces[1] == "..." and (indeces[0] + indeces[2]).isdigit():

                for index in range(int(indeces[0]), int(indeces[2])):

                    file = flac_files[int(index)-1]
                    metadata = analyze_flac(file)

                    if metadata == 'continue':
                        continue
                    else:
                        insert_data(cursor, metadata)
                break

            # Else if user provides list of numbers, analyze those
            if re.sub(r"[\[\],…]", "", selection).isdigit():

                for index in indeces:

                    file = flac_files[int(index)-1]
                    metadata = analyze_flac(file)

                    if metadata == 'continue':
                        continue
                    else:
                        insert_data(cursor, metadata)
                break
            
        # Lastly, if the input is a digit (non-zero), analyze that indexed file
        if selection.isdigit():

            selection = int(selection)
            file = flac_files[selection-1]
            metadata = analyze_flac(file)

            if metadata != "continue":
                insert_data(cursor, metadata)

            break

        print("Invalid choice, please try again.")

# Keep in mind that this DB system need not be fully safeguarded, we are
# working under the assumption that this data is disposable and can be 
# retrieved again (at any time) with a full PC scan.
def do_overwrite_db(conn: sqlite3.Connection, cursor: sqlite3.Cursor):

    try:
        while True:

            do_overwrite = input("Do you want to overwrite the database? (y/n) > ")

            create_backup_sql(conn)

            if do_overwrite.lower() in ['y', 'yes']:
                cursor.executescript("DROP TABLE IF EXISTS flac_file")
                create_table(cursor)
                break

            elif do_overwrite.lower() in ['n', 'no']:
                break
    
    except Exception as err:
        print(err)
        conn.close()
    
# Main entry function
def main():

    print("Welcome! Press Ctrl+C at any point to exit the program.\n")

    database = create_db()
    db_connection = database[0]
    db_cursor = database[1]
    create_table(db_cursor)

    try:
        flac_files = search_pc_or_directory()
        do_overwrite_db(db_connection, db_cursor)
        print_files_menu(flac_files)
        analyze_files_menu(db_cursor, flac_files)
    except Exception as err:
        db_connection.close()
        print(err)

    db_connection.commit()
    db_connection.close()

# Begin
if __name__ == "__main__":

    os.system('cls')
    main() 
    del loading_anim_thread
