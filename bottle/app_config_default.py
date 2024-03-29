"""  app_config.py

File containing a directory  of configuration information for the application
"""
import os

app_config = dict()
app_config["HOST"] = "0.0.0.0"
app_config["PORT"] = 8082
app_config["GRAPH_PATH"] = "./graphs/"
app_config["RECORDS_PATH"] = "./records/"
app_config["STATIC_PATH"] = "./static/"
app_config["MANIFEST_FILE"] = "manifest.js"
app_config["OVERLAY_FILE"] = "date_overlay.png"
app_config["CUM_SPECIES_GRAPH"] = "cum_species_graph"
app_config["BY_MONTH_GRAPH"] = "by_month_graph"
app_config["LOG_PATH"] = "./log/"
app_config["LOG_FILE"] = "moth_bottle.log"
app_config["REQUESTS_LOG_FILE"] = "requests.log"
app_config["TAXONOMY_TABLE"] = "irecord_taxonomy"
app_config["DB_UPDATE_TIME_FILE"] = "db_update_time.flag"


# Test paths exist and create them if missing
try:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
except FileNotFoundError:
    pass  # Hack - this is the second time this has been called.

# Test paths exist and create them if missing
for k, v in app_config.items():
    if "PATH" in k:
        try:
            os.mkdir(v)
        except FileExistsError:
            pass
