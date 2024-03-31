import argparse
from pathlib import Path

from .metasutil import api
from .metasutil import log

def main():

    # Instantiate
    parser = argparse.ArgumentParser(
        description='metasift'
    )

    # Silent mode
    parser.add_argument(
        '-s',
        '--silent',
        action='store_true',
        help='enables silent mode; mutes all success & error messages'
    )

    # Small wrapper groups for --help readability purposes
    search_wrapper = parser.add_argument_group(
        title='search methods'
    )
    write_wrapper = parser.add_argument_group(
        title='write methods'
    )

    # Inner exclusive groups
    search_methods = search_wrapper.add_mutually_exclusive_group(required=True)
    write_methods = write_wrapper.add_mutually_exclusive_group(required=True)

    # Write methods - how should we write to the DB?
    write_methods.add_argument(
        '-a', 
        '--append', 
        action='store_true',
        help='append unique results to database'
    )
    write_methods.add_argument(
        '-o', 
        '--overwrite', 
        action='store_true',
        help='write over current database contents'
    )

    # Optional argument, user can provide their own DB file if desired
    parser.add_argument(
        '-db',
        metavar='path',
        default=api.DEFAULT_DATABASE_PATH, # cwd/data
        type=Path,
        help='path to sqlite database, creates one in given path if none exist'
    )

    # Search within a directory recursively (include subfolders)
    search_methods.add_argument(
        '-r', 
        '--recursive', 
        action='store_true',
        help='search given directory(ies) recursively'
    )

    # Search within a directory non-recursively (ignore subfolders)
    search_methods.add_argument(
        '-n', 
        '--nonrecursive',
        action='store_true',
        help='search given directory(ies) non-recursively'
    )

    # Search all disk partitions
    search_methods.add_argument(
        '-e', 
        '--everything', 
        action='store_true',
        help='search the entirety of the system'
    )

    # Can be a list or a single item, directory for 
    parser.add_argument(
        'path',
        metavar='dir',
        nargs='*',
        type=Path,
        default=[api.DEFAULT_SEARCH_PATH],
        help='directory(ies) to perform search within'
    )

    args = parser.parse_args()    

    print("MetaSift - Beginning search...")
    api.handle_main(args)
    print("MetaSift has completed sift & store procedures.")
    
    log.cleanup()
    
if __name__ == "__main__":
    main()