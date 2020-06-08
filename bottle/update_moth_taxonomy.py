""" update_moth_taxonmy.py"

This module acts as an upgrade mechanism for the irecord_taxonomy table in the database

This module will check for files with the name YYYYMMDD_irecord_names.csv
Using the date in the name it will check against any stored date.
If the new date is newer (or old date doesn't exist) the irecord_taxonomy table
will be (re)written.

"""
import pandas as pd
import mysql.connector as mariadb
import os
import datetime as dt
import glob

os.chdir(os.path.dirname(os.path.abspath(__file__)))
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
        for n in names.MothName:
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
        last_update_date
        and newest_table_date
        and int(newest_table_date) > int(last_update_date)
    ) or (newest_table_date and not last_update_date):
        print("Finally decided to update table")
        print(f"Last update: {last_update_date or 'Never!'}")
        print(f"Latest list: {newest_table_date or 'Not found!'}")
    else:
        newest_table_name = False

    return newest_table_name


def update_table(tablename, filename):
    cnx = mariadb.connect(**sql_config)
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
        for _, *row in names_df.itertuples():
            cursor.execute(
                f"INSERT INTO {tablename} ({cols}) VALUES ({subs});", tuple(row)
            )
            taxon = f"{row[mgi]} {row[msi]}"
            if row[mni] != taxon:
                # print((taxon, *row[1:]))
                cursor.execute(
                    f"INSERT INTO {tablename} ({cols}) VALUES ({subs});",
                    (taxon, *row[1:]),
                )

    except ModuleNotFoundError:
        rv = False

    cnx.close()
    cursor.close()

    return rv


def get_table(sql_query):
    """ Creates a pandas DataFrame from a SQL Query"""

    # Establish a connection to the SQL server
    # print(sql_config)
    cnx = mariadb.connect(**sql_config)
    cursor = cnx.cursor()

    cursor.execute(sql_query)
    data_list = [list(c) for c in cursor]
    count_df = pd.DataFrame(data_list, columns=list(cursor.column_names))

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

    cnx = mariadb.connect(**sql_config)
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


def update_table_moth_taxonomy():
    # TODO Turn off auto commit so we can roll back if issues are found

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
