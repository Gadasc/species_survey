""" update_moth_taxonmy.py"

This module acts as an upgrade mechanism for the irecord_taxonomy table in the database

This module will check for files with the name YYYYMMDD_irecord_names.csv
Using the date in the name it will check against any stored date.
If the new date is newer (or old date doesn't exist) the irecord_taxonomy table
will be (re)written.

History
-------
14 July 2022 - Added support for sqlite3
14 July 2020 - Added code to add the recorder, location and trap tables
26 June 2020 - Added indexes
20 June 2020 - Made sure list going into common_names.js is sorted.
   June 2020 - Genesis

"""

import datetime as dt
import glob
import logging
import mysql.connector as mariadb
import os
import pandas as pd
import sqlite3
import warnings

# Can't call this twice without messing things up.
# TODO: get rid of the global variables and
# pass a reference to sql_config and app_config
# os.chdir(os.path.dirname(os.path.abspath(__file__)))
try:
    from sql_config_local import sql_config
except ModuleNotFoundError:
    from sql_config_default import sql_config

try:
    from app_config_local import app_config as cfg
except ModuleNotFoundError:
    from app_config_default import app_config as cfg


cfg["IRECORD_TABLE_DATE_FILE"] = "last_irecord_table_update.log"


def update_mothnames():
    """ Updates /static/common_names.js
    """
    names = get_table(f"SELECT MothName from {cfg['TAXONOMY_TABLE']};")

    with open("./static/common_names.js", "w") as fnames:
        fnames.write("var common_names = [")
        for n in sorted(names.MothName):
            fnames.write('"' + n + '", ')
        fnames.write("];")


def update_check():
    last_update_date = False
    newest_table_date = False
    newest_table_name = False

    # Determine if we need to update by first finding last time the table was updated
    try:
        last_update_date = dt.datetime.fromtimestamp(
            os.path.getmtime(cfg["IRECORD_TABLE_DATE_FILE"])
        ).strftime("%Y%m%d")
        print(f"Last update date: {last_update_date}")
    except FileNotFoundError:
        print("No record of updating table so I think I will do it.")

    # Now search for updated tables.
    try:
        newest_table_name = sorted(glob.glob("[0-9]*_irecord_names.csv"))[-1]
        print("Last list filename:", newest_table_name)
        newest_table_date = newest_table_name.split("_", maxsplit=1)[0]
        if len(newest_table_date) != 8 or not newest_table_date.isnumeric():
            newest_table_date = False
    except IndexError:
        pass

    if (
        newest_table_date
        and int(newest_table_date) > int(last_update_date)
        or newest_table_date
        and not last_update_date
    ):
        print("Finally decided to update table")
        print(f"Last update: {last_update_date or 'Never!'}")
        print(f"Latest list: {newest_table_date or 'Not found!'}")
    else:
        newest_table_name = False

    return newest_table_name


def get_db_connection():
    if cfg["USE_SQLITE"]:
        cnx = sqlite3.connect(cfg["SQLITE_PATH"] + cfg["SQLITE_FILE"])
    else:
        cnx = mariadb.connect(**sql_config)
    return cnx


def update_table(tablename, filename):
#    cnx = mariadb.connect(**sql_config)
    cnx = get_db_connection()
    cursor = cnx.cursor()
    rv = True

    try:

        names_df = pd.read_csv(filename).fillna("")
        names_df.sort_values("MothName", inplace=True)

        # Create and populate moth_taxonomy
        cursor.execute(f"DROP TABLE IF EXISTS {tablename};")
        command = (
            f"CREATE TABLE {tablename} (Id INT AUTO_INCREMENT PRIMARY KEY, "
            f"{' VARCHAR(50) DEFAULT NULL, '.join(names_df.columns)}"
            f" VARCHAR(50) DEFAULT NULL"
            f");"
        )
        print(command)
        cursor.execute(command)

        cols = ",".join(names_df.columns)
        subs = ",".join(["%s"] * len(names_df.columns))
        print(cols)
        print(names_df.columns)
        mgi = list(names_df.columns).index("MothGenus")
        msi = list(names_df.columns).index("MothSpecies")
        mni = list(names_df.columns).index("MothName")
        print(mgi, msi)
        # Avoid duplicating scientific name entries
        taxons_added = set()
        for _, *row in names_df.itertuples():
            cursor.execute(
                f"INSERT INTO {tablename} ({cols}) VALUES ({subs});", tuple(row)
            )
            taxon = f"{row[mgi]} {row[msi]}"
            if row[mni] != taxon and taxon not in taxons_added:
                # print((taxon, *row[1:]))
                cursor.execute(
                    f"INSERT INTO {tablename} ({cols}) VALUES ({subs});",
                    (taxon, *row[1:]),
                )
                taxons_added.add(taxon)

    except ModuleNotFoundError:
        rv = False

    cnx.close()
    cursor.close()

    return rv


def get_table(sql_query):
    """ Creates a pandas DataFrame from a SQL Query"""

    # Establish a connection to the SQL server
    # print(sql_config)
    #cnx = mariadb.connect(**sql_config)
    cnx = get_db_connection()
    cursor = cnx.cursor()

    try:
        cursor.execute(sql_query)
    except:
        logging.error(f"{sql_query} raised an SQL issue!")
        raise

    data_list = [list(c) for c in cursor]

    if cfg["USE_SQLITE"]:
        try: 
            columns = [c[0] for c in cursor.description]
        except TypeError:
            columns = None
            logging.warn(f"{sql_query} does not generate a table!")
        except sql.OperationalError:
            logging.error(f"{sql_query} raised an SQL issue!")
            raise
    else:
        columns = list(cursor.column_names)

    count_df = pd.DataFrame(data_list, columns=columns)

    cursor.close()
    cnx.close()
    return count_df


def update_records(mapfile_name):
    """ Now the irecord_taxonomy table exists check the records have a name for each
        Issues will exist where the old moth name does not map to a new one.
        e.g. Pugs agg. ignore these - despite causing issues later
    """
    # load map
    moth_map = pd.read_csv(mapfile_name, index_col="ukmoths", squeeze=True).to_dict()

    # Get list of names in records
    unique_names = get_table("SELECT MothName FROM moth_records GROUP BY MothName;")

#    cnx = mariadb.connect(**sql_config)
    cnx = get_db_connection()
    cursor = cnx.cursor()

    for mname in unique_names["MothName"]:
        if mname is None:
            continue
        # If name doesn't exist in latest taxonomy table, check for a map
        test_species = get_table(
            f'SELECT MothName FROM {cfg["TAXONOMY_TABLE"]} WHERE MothName="{mname}";'
        )
        if test_species.empty:
            print(f"Unknown name: {mname} ==> {moth_map.get(mname, mname)}", end="")
            if mname in moth_map:
                print()
                cursor.execute(
                    f"""UPDATE moth_records SET MothName = "{moth_map[mname]}"
                        WHERE MothName = "{mname}";"""
                )
            else:
                print("\u001b[31m X \u001b[0m")

    cursor.close()
    cnx.close()
    return True


def set_column_default(col_name, def_value):
    """ Encapsulates the methods for updating the column defaults
    """

    if def_value in ["NULL", None, ""]:  # Seems hacky to me but "NULL" won't work
        print("Really setting defauly to NULL")
        get_table(f"""ALTER TABLE moth_records ALTER {col_name} SET DEFAULT NULL;""")
    else:
        get_table(
            f"""ALTER TABLE moth_records ALTER {col_name} SET DEFAULT "{def_value}";"""
        )

    # If any entries are NULL set to default
    get_table(
        f'UPDATE moth_records SET {col_name}="{def_value}"'
        f' WHERE  {col_name} IN (NULL, "NULL", "", "None");'
    )


def get_column_default(col_name):
    """ Encapsulates the retrieval of a column default value
    """
    if cfg["USE_SQLITE"]:
        records_description = get_table("PRAGMA table_info(moth_records);").set_index("name")
        try:
            rv = records_description.loc[col_name]["dflt_value"]
        except KeyError:
            rv = None
        
    else:
        records_description = get_table("DESCRIBE moth_records;").set_index("Field")
        try:
            rv = records_description.loc[col_name]["Default"]
        except KeyError:
            rv = None

    return rv


def update_table_moth_taxonomy():
    # TODO Turn off auto commit so we can roll back if issues are found

    # TODO Move to a function to ensure the databases are up to date
    get_table(
        f"CREATE INDEX IF NOT EXISTS tax_MothName ON {cfg['TAXONOMY_TABLE']}(MothName);"
    )
    get_table(f"CREATE INDEX IF NOT EXISTS tax_TVK ON {cfg['TAXONOMY_TABLE']}(TVK);")
    get_table(f"CREATE INDEX IF NOT EXISTS rec_MothName ON moth_records(MothName);")
    get_table(f"CREATE INDEX IF NOT EXISTS rec_Date ON moth_records(Date);")

    # Ensure additional columns exist - don't set default.
    # If no value set, then it will get automatically updated when the first
    # default is set.
    if not cfg["USE_SQLITE"]:
        get_table("ALTER TABLE moth_records ADD COLUMN IF NOT EXISTS" " Recorder CHAR(30);")
        get_table("ALTER TABLE moth_records ADD COLUMN IF NOT EXISTS" " Trap CHAR(30);")
        get_table("ALTER TABLE moth_records ADD COLUMN IF NOT EXISTS" " Location CHAR(30);")
    else:
        # SQLITE doesn't support the IF NOT EXISTS clause on ALTER TABLE
        try:
            get_table("ALTER TABLE moth_records ADD COLUMN Recorder CHAR(30);")
        except sqlite3.OperationalError:
            pass
        try:
            get_table("ALTER TABLE moth_records ADD COLUMN Trap CHAR(30);")
        except sqlite3.OperationalError:
            pass
        try:
            get_table("ALTER TABLE moth_records ADD COLUMN Location CHAR(30);")
        except sqlite3.OperationalError:
            pass
        warnings.warn("FUTURE PROOFING: Need to add code to handle the addition of new columns")

    # Create supplimentaty tables for Recorders, Traps and Locations.
    get_table("CREATE TABLE IF NOT EXISTS recorders_list (Recorder CHAR(30) NOT NULL);")
    get_table("CREATE TABLE IF NOT EXISTS traps_list (Trap CHAR(30) NOT NULL);")
    get_table(
        "CREATE TABLE IF NOT EXISTS locations_list "
        "(Name CHAR(30) NOT NULL, OSGB_Grid CHAR(15));"
    )

    # Main function starts here
    #
    # Check if an updated list exists
    update_list_file = update_check()
    if not update_list_file:
        return

    # If we have an updated list check to see there is a corresponding map file
    mapfile_name = f"{update_list_file[0:8]}_map_ukmoths_to_irec.csv"
    try:
        with open(mapfile_name):
            print("Updating table using", update_list_file)
            if not update_table(cfg["TAXONOMY_TABLE"], update_list_file):
                print(f"Failed update_table {cfg['TAXONOMY_TABLE']} {update_list_file}")
                return
            if not update_records(mapfile_name):
                print(f"Failed update_records {mapfile_name}")
                return
            with open(cfg["IRECORD_TABLE_DATE_FILE"], "w"):
                pass  # Touch the file to store update
        update_mothnames()
    except FileNotFoundError:
        print("Missing map file!")
        return


if __name__ == "__main__":
    update_table_moth_taxonomy()
