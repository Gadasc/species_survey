import mysql.connector
import pandas as pd

from sql_config import sql_config

moth_names = "./20200429_moth_names_all.csv"

cnx = mysql.connector.connect(**sql_config)
cursor = cnx.cursor()


# Create records table
try:
    cursor.execute("DROP TABLE IF EXISTS moth_records;")
    cursor.execute(
        "CREATE TABLE  moth_records "
        "(Id INT AUTO_INCREMENT PRIMARY KEY, Date DATE, MothName VARCHAR(50) "
        "DEFAULT NULL, MothCount INT default 0);"
    )
    cursor.execute("describe moth_records;")
    for x in cursor:
        print(x)
except Exception as e:
    print(e)




names_df = pd.read_csv(
    moth_names,
    header=None,
    names=["Common", "Family", "Sub-family", "Genus", "Species"],
).fillna("")
names_df.sort_values("Common", inplace=True)

# Create and populate moth_taxonomy
cursor.execute("DROP TABLE IF EXISTS moth_taxonomy;")
cursor.execute(
    "CREATE TABLE moth_taxonomy (Id INT AUTO_INCREMENT PRIMARY KEY,"
    "MothName VARCHAR(50),"
    "MothFamily VARCHAR(50) DEFAULT NULL,"
    "MothSubFamily VARCHAR(50) DEFAULT NULL,"
    "MothGenus VARCHAR(50) DEFAULT NULL,"
    "MothSpecies VARCHAR(50) DEFAULT NULL"
    ");"
)

cols = ",".join(["MothName", "MothFamily", "MothSubFamily", "MothGenus", "MothSpecies"])

print(cols)
print(names_df.columns)
for _, *row in names_df.itertuples():

    print(tuple(row))
    cursor.execute(
        f"INSERT INTO moth_taxonomy ({cols}) VALUES (%s,%s,%s,%s,%s);", tuple(row)
    )

cursor.execute("DESCRIBE moth_taxonomy;")
for t in cursor:
    print(t)


cnx.close()
