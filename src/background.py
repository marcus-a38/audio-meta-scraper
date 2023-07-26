##################################################################################
#================================================================================#                                                                                #
# Author: Marcus Antonelli | GitHub: /marcus-a38 | E-Mail: marcus.an38@gmail.com #
#================================================================================#                
#                Most Recent Publish Date: 7/25/2023 (version 2)                 #
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

from metaflac import \
    search_whole_pc, analyze_flac, analyze_mpeg4, \
    create_db, create_table, insert_data, create_backup_sql

def main():

    drive_results_gen = search_whole_pc()
    database = create_db()
    conn = database[0]
    cursor = database[1]

    create_backup_sql(conn)
    cursor.executescript("DROP TABLE IF EXISTS audio_metadata")
    create_table(cursor)
    
    for drive in drive_results_gen:
        for file_type in drive: 
            # This can likely be reworked, since we're searching 
            # through FLACs and MPEGs separately anyways
            for file in file_type:
                if file.endswith('.flac'):
                    analyzed_file = analyze_flac(flac_path=file, silent=True)
                else:
                    analyzed_file = analyze_mpeg4(mpeg4_path=file, silent=True)

                if analyzed_file == "continue":
                    continue
                insert_data(cursor, data=analyzed_file)

    conn.commit()
    conn.close()

main()
