import sqlite3 as sql

from app_config_default import app_config as cfg


cnx = sql.connect(cfg["SQLITE_PATH"] + cfg["SQLITE_FILE"])
csr = cnx.cursor()


# Get the taxonomic list
taxa = csr.execute('SELECT * from irecord_taxonomy WHERE MothFamily LIKE "Sphin%";')
for r in  taxa:
    print(r)


# Get column names
cols = csr.execute('SELECT name FROM PRAGMA_TABLE_INFO("irecord_taxonomy");')
print([n[0] for n in cols])

