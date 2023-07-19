##################################################################################
#================================================================================#
# Author: Marcus Antonelli | GitHub: /marcus-a38 | E-Mail: marcus.an38@gmail.com #
#================================================================================#
#                Most Recent Publish Date: 7/19/2023 (version 1)                 #
#================================================================================#
#                                                                                #
#                               -- DISCLAIMER --                                 #
#                                                                                #
#     You may not use this script commercially without the author's consent      #
#         All changes made to the original content of this script must be        #
#          documented in the open source material (non-commercial use.)          #
#     This script offers no warranty, nor does the author hold any liability     #
#     for issues that may be encountered or caused by the use of this script.    #
#                                                                                #
#================================================================================#
##################################################################################

from metaflac \
    import search_whole_pc, analyze_flac, create_db, create_table, insert_data, create_backup_sql

# First version of the scheduled scanning program that will search the entire PC and update the DB daily

def main():

    flac_files = search_whole_pc()
    database = create_db()
    conn = database[0]
    cursor = database[1]

    create_backup_sql(conn)
    cursor.executescript("DROP TABLE IF EXISTS flac_file")
    create_table(cursor)
    
    for flac_file in flac_files:
        analyzed_file = analyze_flac(flac_path=flac_file, silent=True)
        if analyzed_file == "continue":
            continue
        insert_data(cursor, data=analyzed_file)

    conn.commit()
    conn.close()

main()
