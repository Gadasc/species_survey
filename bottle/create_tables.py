import copy
import getpass
import glob
import mysql.connector
import pandas as pd

try:
    from sql_config_local import sql_config
except ModuleNotFoundError:
    from sql_config_default import sql_config

# find latest file to create taxonomy tables
moth_names = max(glob.glob("????????_irecord_names.csv"))
print("Using input file:", moth_names)

# Generate root login
root_config = copy.deepcopy(sql_config)
del root_config["database"]
root_config["user"] = "root"
root_config["password"] = getpass.getpass(prompt="Database root password:")

cnx = mysql.connector.connect(**root_config)
del root_config["password"]
cursor = cnx.cursor()

# Create database (if it doesn't exist)
cursor.execute(f"CREATE DATABASE IF NOT EXISTS {sql_config['database']};")
cursor.execute(
    f"""CREATE USER IF NOT EXISTS '{sql_config["user"]}'@'localhost' 
    IDENTIFIED BY '{sql_config["password"]}';"""
)
cursor.execute(
    f"""GRANT ALL PRIVILEGES ON {sql_config['database']}.* 
    TO '{sql_config["user"]}'@'localhost';"""
)
cursor.execute("FLUSH PRIVILEGES;")
cursor.close()
cnx.close()

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
    names=["Common", "Family", "Sub-family", "Genus", "Species","TVK"],
).fillna("")
names_df.sort_values("Common", inplace=True)

# Create and populate moth_taxonomy
cursor.execute("DROP TABLE IF EXISTS irecord_taxonomy;")
cursor.execute(
    "CREATE TABLE irecord_taxonomy (Id INT AUTO_INCREMENT PRIMARY KEY,"
    "MothName VARCHAR(50),"
    "MothFamily VARCHAR(50) DEFAULT NULL,"
    "MothSubFamily VARCHAR(50) DEFAULT NULL,"
    "MothGenus VARCHAR(50) DEFAULT NULL,"
    "MothSpecies VARCHAR(50) DEFAULT NULL,"
    "TVK VARCHAR(50) DEFAULT NULL"
    ");"
)

cols = ",".join(["MothName", "MothFamily", "MothSubFamily", "MothGenus", "MothSpecies", "TVK"])

print(cols)
print(names_df.columns)
for _, *row in names_df.itertuples():

    print(tuple(row))
    cursor.execute(
        f"INSERT INTO irecord_taxonomy ({cols}) VALUES (%s,%s,%s,%s,%s,%s);", tuple(row)
    )

cursor.execute("DESCRIBE irecord_taxonomy;")
for t in cursor:
    print(t)


cnx.close()
