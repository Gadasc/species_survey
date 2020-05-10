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

# Test paths exist and create them if missing
for k, v in app_config.items():
    if "PATH" in k:
        try:
            os.mkdir(v)
        except FileExistsError:
            pass
