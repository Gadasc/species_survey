#! /usr/local/bin/python3.7

"""
moth_bottle.py

Install by adding the following to crontab - replacing PATH
appropriately and setting u+x permissions:

@reboot PATH/moth_bottle.py &

History
-------
14 Sep 2019 - add summary page
08 Sep 2019 - Now allows data to be modified by adding date YYYY-MM-DD to /survey/
07 Sep 2019 - Fine tuning table to only remove singletons.
18 Aug 2019 - moving back to RPi and generating manifest file on the fly.
15 Aug 2019 - Combining functions to update database
13 Aug 2019 - Adding route page and working out how to add javascript
20 Jul 2019 - starting to optimise so graphs aren't redrawn unless required.
16 Jul 2019 - Profiling using werkzeug
13 Jul 2019 - Initial trial page producing a table and graph of catches.

"""

from app_config import app_config as cfg
import bottle
from bottle import Bottle, template, static_file, request, TEMPLATE_PATH
import pandas as pd
import mysql.connector as mariadb
from sql_config import sql_config
import datetime as dt
import matplotlib.pyplot as plt
from matplotlib.dates import MonthLocator, DateFormatter
import numpy as np

# from werkzeug.middleware.profiler import ProfilerMiddleware
import os
import json
import html

os.chdir(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH.insert(0, os.getcwd())

# Format information for plot
plot_dict = {"figsize": (10, 4.5)}

GRAPH_PATH = cfg["GRAPH_PATH"]
OVERLAY_FILE = cfg["OVERLAY_FILE"]
STATIC_PATH = cfg["STATIC_PATH"]


def refresh_manifest():
    """ Check the javascript manifest.js file is up to date """
    today = dt.date.today()
    try:
        if (
            dt.date.fromtimestamp(
                os.path.getmtime(cfg["STATIC_PATH"] + cfg["MANIFEST_FILE"])
            )
            == today
        ):
            print("Today's manifest exists - returning.")
            return
    except FileNotFoundError:
        pass

    # By getting here we have to update the manifest file.
    # Get moths and quantity found in the last 2 weeks
    cnx = mariadb.connect(**sql_config)
    cursor = cnx.cursor()
    cursor.execute(
        f"SELECT MothName species, sum(MothCount) recent FROM moth_records WHERE "
        "Date > DATE_ADD(NOW(), INTERVAL -14 DAY) GROUP BY species;"
    )

    records_dict = {row: line for row, line in enumerate(cursor)}
    recent_df = pd.DataFrame.from_dict(
        records_dict, columns=["species", "recent"], orient="index"
    )

    # generate javascript file to be sent to broswers
    with open(cfg["STATIC_PATH"] + cfg["MANIFEST_FILE"], "w") as mout:
        mout.write("var recent_moths  = [\n")
        for _, r in recent_df.iterrows():
            mout.write(f'    {{species:"{r.species}", recent:{r.recent}, count:0 }},\n')
        mout.write("];")


def update_moth_database(cursor, sql_date_string, dict_records):
    """ Update the mysql server with the latest records
    """
    # delete any records for today
    cursor.execute("DELETE FROM moth_records WHERE Date = %s;", (sql_date_string,))

    if not dict_records:
        # If no moths recorded, add a null entry to identify we did trap on this date.
        cursor.execute(
            "INSERT INTO moth_records (Date) VALUES (%s);", (sql_date_string,)
        )
    else:
        # add updates
        ins_list = [
            '("{}", "{}", {})'.format(sql_date_string, k.replace("_", " "), v)
            for k, v in dict_records.items()
        ]

        ins_string = ", ".join(ins_list)
        cursor.execute(
            "INSERT INTO moth_records (Date, MothName, MothCount) VALUES {};".format(
                ins_string
            )
        )


def generate_records_file(cursor, date_dash_str):
    """ Ensure the records file cfg['RECORD_PATH'] exists
        This file contains the {moth(with underscords): count:str} dict in json form
    """
    columns = ["MothName", "MothCount"]
    cursor.execute(
        f"SELECT {','.join(columns)} FROM moth_records where Date='{date_dash_str}';"
    )
    records_dict = {}
    for mn, mc in cursor:
        print(f"{mn}: {str(mc)}")
        records_dict[mn.replace(" ", "_")] = str(mc)

    print(records_dict)
    with open(
        f"{cfg['RECORDS_PATH']}day_count_{date_dash_str.replace('-','')}.json", "w"
    ) as json_out:
        json_out.write(json.dumps(records_dict))


def show_latest_moths(cursor):
    """ Generate a table showing the latest records.
        Because we are using mysql.connector instead sqlalchemy which ORM we
        need to query the database with an SQL string and build the recent
        sightings table."""

    columns = ["Date", "MothName", "MothCount"]
    # mothname_col = columns.index("MothName")

    cursor.execute(
        f"SELECT {', '.join(columns)} FROM moth_records WHERE "
        "Date > DATE_ADD(NOW(), INTERVAL -14 DAY);"
    )
    records_dict = {row: line for row, line in enumerate(cursor)}

    recent_df = pd.DataFrame.from_dict(records_dict, columns=columns, orient="index")
    recent_df["MothName"] = recent_df["MothName"].apply(
        lambda mn: f'<a href="/species/{mn}">{mn}</a>'
    )
    recent_df["Date"] = recent_df["Date"].apply(
        lambda dd: f'<a href="/survey/{dd}">{dd}</a>'
    )
    recent_df.set_index(["Date", "MothName"], inplace=True)

    return recent_df.unstack("Date").fillna("").to_html(escape=False, justify="left")


def get_moth_catches(moth_name: str):
    query_str = (
        f"select Date, MothCount from moth_records "
        f'where MothName like "{moth_name}" group by Date;'
    )

    # Establish a connection to the SQL server
    cnx = mariadb.connect(**sql_config)
    cursor = cnx.cursor()

    cursor.execute(query_str)
    columns = list(cursor.column_names)
    # debug(columns)

    data_list = [list(c) for c in cursor]
    survey_df = pd.DataFrame(data_list, columns=columns)
    cursor.close()
    cnx.close()

    return survey_df


def get_moths_list():
    query_str = f"SELECT MothName FROM moth_records GROUP BY MothName;"

    # Establish a connection to the SQL server
    cnx = mariadb.connect(**sql_config)
    cursor = cnx.cursor()

    cursor.execute(query_str)
    columns = list(cursor.column_names)
    # debug(columns)

    data_list = [list(c) for c in cursor]
    survey_df = pd.DataFrame(data_list, columns=columns)
    return survey_df


def graph_date_overlay():
    """ Determine if the date overlay graph is old and regenerate if necessary."""

    today = dt.date.today()
    try:
        if (
            dt.date.fromtimestamp(
                os.path.getmtime(cfg["GRAPH_PATH"] + cfg["OVERLAY_FILE"])
            )
            == today
        ):
            print("Today's overlay exists - returning.")
            return
    except FileNotFoundError:
        pass

    fig = plt.figure(**plot_dict)
    ax = fig.add_subplot(111)
    ax.set_xlim(today.replace(month=1, day=1), today.replace(month=12, day=31))
    ax.xaxis.set_major_locator(MonthLocator())
    ax.xaxis.set_major_formatter(DateFormatter("%b"))
    plt.setp(ax.xaxis.get_majorticklabels(), ha="left")
    ax.axvline(today, color="grey", linestyle="--")
    plt.axis("off")
    plt.savefig(GRAPH_PATH + OVERLAY_FILE, transparent=True)
    plt.close()


def get_db_update_time():
    """ Return a datetime.datetime object with the update time of the database
        This only works on some db engines - recent versions of mariadb but not myql
    """
    cnx = mariadb.connect(**sql_config)
    cursor = cnx.cursor()
    cursor.execute(
        "SELECT update_time FROM information_schema.tables "
        f"WHERE TABLE_SCHEMA = 'cold_ash_moths' "
        f"AND table_name = 'moth_records';"
    )
    update_time, = cursor.fetchone()
    print(update_time)
    cursor.close()
    cnx.close()
    return update_time


def graph_mothname_v2(mothname):
    catches_df = get_moth_catches(mothname)

    # Test results
    print(f"Latest date: {catches_df.Date.max()}")
    try:
        print(
            f"{mothname}.png modified: "
            f'{dt.date.fromtimestamp(os.path.getmtime(f"{GRAPH_PATH}{mothname}.png"))}'
        )
    except FileNotFoundError:
        print(f"{mothname}.png missing!")

    try:
        if catches_df.Date.max() < dt.date.fromtimestamp(
            os.path.getmtime(f"{GRAPH_PATH}{mothname}.png")
        ):
            print(f"File is new enough. Not updating {mothname}")
            return
    except FileNotFoundError:
        print(f"Unable to find {GRAPH_PATH}{mothname}.png so will create it.")

    # If a moth was caught today the graph will be updated.
    # So find out if the graph is newer than the last database update,
    # if so we don't recreate
    try:
        file_update_time = dt.datetime.fromtimestamp(
            os.path.getmtime(f"{GRAPH_PATH}{mothname}.png")
        )
        print(f"File: {mothname}.png was updated: {file_update_time}")
        db_update_time = get_db_update_time()
        print(f"Database:            was updated: {db_update_time}")
        if file_update_time > db_update_time:
            return
    except (FileNotFoundError, TypeError):
        print("File still not found")

    today = dt.date.today()
    date_year_index = pd.DatetimeIndex(
        pd.date_range(
            start=today.replace(month=1, day=1), end=today.replace(month=12, day=31)
        )
    )

    this_year_df = (
        catches_df[catches_df["Date"] >= today.replace(month=1, day=1)]
        .set_index("Date")
        .reindex(date_year_index, fill_value=0)
        .reset_index()
    )

    catches_df["Date"] = [d.replace(year=today.year) for d in catches_df["Date"]]
    flattened_df = catches_df.groupby("Date").mean()

    all_catches_df = flattened_df.reindex(date_year_index, fill_value=0).reset_index()
    x = all_catches_df.values[:, 0]
    y_all = all_catches_df.values[:, 1]
    y_this = this_year_df.values[:, 1]
    print(str(plot_dict))
    fig = plt.figure(**plot_dict)
    ax = fig.add_subplot(111)
    ax.set_title(mothname)
    ax.plot(x, y_all, label="Average")
    ax.plot(x, y_this, "r", label=str(today.year))
    ax.legend()
    ax.set_xlim(all_catches_df.values[0, 0], all_catches_df.values[-1, 0])
    ax.set_ylim(bottom=0)
    ax.xaxis.set_major_locator(MonthLocator())
    ax.xaxis.set_major_formatter(DateFormatter("%b"))
    plt.setp(ax.xaxis.get_majorticklabels(), ha="left")
    plt.savefig(f"{GRAPH_PATH}{mothname}.png")
    plt.close()


app = Bottle()


@app.route("/graphs/<species>")
def server_graphs(species):
    """ Helper route to return a graph image as a static file. """
    species = species.replace("%20", " ")
    return static_file(f"{species}.png", root=cfg["GRAPH_PATH"])


@app.route("/")
def index():
    """ Landing page for the web site. """
    # Display a landing page
    return template("index.tpl")


@app.route("/static/<filename>")
def service_static_file(filename):
    """ Help route to return static files. """
    return static_file(f"{filename}", root=cfg["STATIC_PATH"])


@app.route("/survey")
@app.route("/survey/<dash_date_str:re:\\d{4}-\\d{2}-\\d{2}>")
def serve_survey(dash_date_str=None):
    """ Generate a survey sheet to records today's results in. """
    cnx = mariadb.connect(**sql_config)
    db = cnx.cursor()

    if dash_date_str:
        generate_records_file(db, dash_date_str)
        # TODO we may want to just remove the manifest to simplify the historical
        # survey sheet.
    else:
        dash_date_str = dt.date.today().strftime("%Y-%m-%d")
        refresh_manifest()  # The manifest shows the moths that could be caught

    try:
        date_str = dash_date_str.replace("-", "")
        with open(f"{cfg['RECORDS_PATH']}day_count_{date_str}.json") as json_in:
            records = json.load(json_in)
    except FileNotFoundError:
        records = {}

    print("Recent moths:", records)
    db.close()
    cnx.close()

    return template("survey.tpl", records=records, dash_date_str=dash_date_str)


@app.route("/summary")
def get_summary():
    """ Display an overall summary for the Moths web-site. """
    today = dt.date.today()

    cnx = mariadb.connect(**sql_config)
    db = cnx.cursor()

    # Update species graph
    db.execute("SELECT year(Date) Year, Date, MothName FROM moth_records;")
    cum_species = pd.DataFrame([list(c) for c in db], columns=list(db.column_names))
    cum_species["Catch"] = 1
    cum_species["Date"] = cum_species["Date"].map(
        lambda dd: dd.replace(year=today.year)
    )
    cum_species.set_index(["Year", "Date", "MothName"], inplace=True)
    cum_results = (
        cum_species.unstack("Date")
        .fillna(method="ffill", axis=1)
        .groupby(by="Year")
        .count()
        .Catch.astype(float)
    )  # Needs to be float for mask to work

    # Finally mask out future dates to avoid the graph plotting a horizontal line to eoy
    cum_results.loc[today.year].mask(
        cum_results.columns > str(today), other=np.NaN, inplace=True
    )
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax = cum_results.transpose().plot(
        marker="", linestyle="-", label="Species Total", **plot_dict
    )
    ax.xaxis.set_major_locator(MonthLocator())
    ax.xaxis.set_major_formatter(DateFormatter("%b"))
    ax.set_xlim([today.replace(month=1, day=1), today.replace(month=12, day=30)])

    # cum_results.transpose().plot()
    plt.savefig(f"{cfg['GRAPH_PATH']}{cfg['CUM_SPECIES_GRAPH']}")
    plt.close()
    # Update catch diversity graph

    # Update catch volume graph

    db.close()
    cnx.close()

    return template(
        "summary.tpl", summary_image_file=cfg["GRAPH_PATH"] + cfg["CUM_SPECIES_GRAPH"]
    )


@app.route("/species/<species>")
def get_species(species):
    """ Generate a summary page for the specified moth species.
        Use % as a wildcard.
    """
    # Establish a connection to the SQL server
    cnx = mariadb.connect(**sql_config)
    db = cnx.cursor()
    species = species.replace("%20", " ")

    query_str = f'SELECT * from moth_records where MothName LIKE "{species}";'
    db.execute(query_str)
    columns = list(db.column_names)
    data_list = [list(c) for c in db]
    db.close()
    cnx.close()

    all_survey_df = pd.DataFrame(data_list, columns=columns)

    # If a wildcard query was resolved to a unique species then replace species with the
    # the unique species
    unique_species = all_survey_df["MothName"].unique()
    if len(unique_species) == 1:
        species = unique_species[0]

        # Produce a graph of these
        graph_date_overlay()
        graph_mothname_v2(species)

        css_graph = "position: relative; top: 0px; left: 0px;"
        return (
            f"<h1>{species}</h1>\n"
            f'<A href="/latest">Recent Catches</A></p>\n'
            f'<div style="position: relative;">\n'
            f'<img style="{css_graph}" src="/graphs/{species}" />\n'
            f'<img style="{css_graph}" src="/graphs/date_overlay" />\n'
            f"</div>\n"
            f'{all_survey_df[["Date", "MothName", "MothCount"]].to_html(index=False)}'
            f"</p>"
        )

    else:
        # There are multiple species - so provide the choice
        return " ".join(
            [
                f'<a href="/species/{specie}">{specie}</a></p>'
                for specie in unique_species
            ]
        )


@app.route("/latest")
def show_latest():
    """ Shows the latest moth catches. """
    # Get a connection to the databe
    cnx = mariadb.connect(**sql_config)

    cursor = cnx.cursor()
    latest_table = show_latest_moths(cursor)
    cnx.close()

    return template("latest.tpl", html_table=latest_table)


@app.post("/handle_survey")
def survey_handler():
    """ Handler to manage the data returned from the survey sheet. """
    records_dir = cfg["RECORDS_PATH"]
    #    today_string = dt.datetime.now()
    date_string = request.forms["dash_date_str"]
    fout_json = records_dir + "day_count_" + date_string.replace("-", "") + ".json"

    rs = list()
    results_dict = dict()
    for moth in request.forms.keys():
        if moth == "dash_date_str":
            continue
        specimens = request.forms.get(
            moth, default=0, index=0, type=int
        )  # leave result as string
        if specimens:
            rs.append(f"<p><strong>{moth}</strong>      {specimens}</p>")
            results_dict[moth] = str(specimens)

    output = "<!DOCTYPE html><html><head><TITLE>Survey Results</TITLE></head>"
    output += "<body><H1>Moths Survey</H1>"
    output += "Date: " + str(date_string) + "</p>"

    # Get a connection to the databe
    cnx = mariadb.connect(**sql_config)
    cursor = cnx.cursor()

    # Store results locally  so when survey sheet is recalled it will auto populate
    with open(fout_json, "w") as fout_js:
        fout_js.write(json.dumps(results_dict))
    # Build table and store resolve in a csv file.
    output += "<table><th>Species</th><th>Count</th>"
    for species, count in results_dict.items():
        output += "<tr><td>{}</td><td>{}<td>".format(species.replace("_", " "), count)

    output += "</table>"
    output += '<a href="/survey">Survey Sheet</a>'

    update_moth_database(cursor, date_string, results_dict)

    # Update a table showing the historical data for last two weeks.
    output += show_latest_moths(cursor)
    output += "</body></html>"

    cnx.close()

    return output


@app.route("/debug")
def debug_info():
    """ Route showing some debug.
    """
    return [str(route.__dict__) + "</p>" for route in app.routes]


@app.route("/help")
def survey_help():
    """ Displays a list of links to possible pages """
    output = str()
    output += "<h1>Survey Help Page</h1>"
    output += "<ul>"
    for route in app.routes:
        label = html.escape(route.rule)
        output += f"<li><a href={label}>{label}</a></li>"
        docstring = route.callback.__doc__
        escstring = (
            "None"
            if not docstring
            else html.escape(docstring).replace("\n", "<br />\n")
        )
        output += f"<ul><li><quote>{escstring}</quote></li></ul>"

        print(route)
    output += "</ul>"
    return output


if __name__ == "__main__":
    #    app = ProfilerMiddleware(app,
    #                             profile_dir = '/var/www/profile',
    #                             filename_format = "moths_bottle_{time}.prof")
    bottle.run(app=app, debug=True, reloader=True, host=cfg["HOST"], port=cfg["PORT"])
