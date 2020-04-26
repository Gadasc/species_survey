#! /usr/local/bin/python3

"""
moth_bottle.py

Install by adding the following to crontab - replacing PATH
appropriately and setting u+x permissions:

@reboot PATH/moth_bottle.py &

History
-------
 4 Apr 2020 - Change column width control to None from -1 due to deprication warning
26 Mar 2020 - Adding timestamp to debug wrapper
13 Mar 2020 - Adding debug wrapper
24 Nov 2019 - Adding summary pages for genus and family
23 Nov 2019 - Adding /family pagesd
21 Nov 2019 - Add /genus page (also good for aggregations)
17 Nov 2019 - Add /species page to show most popular species
10 Nov 2019 - On submit - redirect to /latest instead of creating a new page
 8 Nov 2019 - Fixing bug where summary graph double counted
 6 Nov 2019 - Filters out 'None' from manifest
 3 Nov 2019 - Added Moth Bingo Grid to summary
28 Sep 2019 - Adding Species by month graph
17 Sep 2019 - Moving species to a view
16 Sep 2019 - Adding logging
15 Sep 2019 - Adding code to avoid updating summary graph unless needed.
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
from bottle import Bottle, template, static_file, TEMPLATE_PATH, request, response
import pandas as pd
import mysql.connector as mariadb
from sql_config import sql_config
import datetime as dt
import matplotlib.pyplot as plt
from matplotlib.dates import MonthLocator, DateFormatter
import numpy as np
import logging
import logging.handlers
from functools import wraps

# from werkzeug.middleware.profiler import ProfilerMiddleware
import os
import json
import html

os.chdir(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH.insert(0, os.getcwd())

# Override the pandas' max display width to prevent to_html truncating cols
pd.set_option("display.max_colwidth", None)

# Format information for plot
plot_dict = {"figsize": (10, 4.5)}

GRAPH_PATH = cfg["GRAPH_PATH"]
OVERLAY_FILE = cfg["OVERLAY_FILE"]
STATIC_PATH = cfg["STATIC_PATH"]

# Collect the logging set up into a common file.
moth_logger = logging.getLogger("moth_logger")
moth_logger.setLevel(logging.DEBUG)

handler = logging.handlers.RotatingFileHandler(
    cfg["LOG_PATH"] + cfg["LOG_FILE"], maxBytes=1024 * 1024, backupCount=7
)
moth_logger.addHandler(handler)


# set up the requests logger
requests_logger = logging.getLogger("requests_logger")
requests_logger.setLevel(logging.INFO)
file_handler = logging.handlers.RotatingFileHandler(
    cfg["LOG_PATH"] + cfg["REQUESTS_LOG_FILE"], maxBytes=1024 * 1024, backupCount=2
)
formatter = logging.Formatter("%(msg)s")
file_handler.setFormatter(formatter)
requests_logger.addHandler(file_handler)


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


def debug(fn):
    @wraps(fn)
    def debug_fn(*args, **kwds):
        moth_logger.debug(f">>>: {dt.datetime.now()} :: {fn.__name__}")
        retcode = fn(*args, **kwds)
        moth_logger.debug(f"<<<: {dt.datetime.now()} :: {fn.__name__}")
        return retcode

    return debug_fn


def log_to_logger(fn):
    """ Wrap a Bottle request so that a log line is emitted after it's handled.
    (This decorator can be extended to take the desired logger as a param.) """

    @wraps(fn)
    def _log_to_logger(*args, **kwargs):
        request_time = dt.datetime.now()
        actual_response = fn(*args, **kwargs)
        # modify this to log exactly what you need:
        requests_logger.info(
            "%s %s %s %s %s"
            % (
                request.remote_addr,
                request_time,
                request.method,
                request.url,
                response.status,
            )
        )
        return actual_response

    return _log_to_logger


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
            moth_logger.debug("Today's manifest exists - returning.")
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

    records_dict = {row: line for row, line in enumerate(cursor) if None not in line}
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
        if mn is None:
            continue  # The latest table shows when no moths were caught

        moth_logger.debug(f"{mn}: {str(mc)}")
        records_dict[mn.replace(" ", "_")] = str(mc)

    moth_logger.debug(records_dict)
    with open(
        f"{cfg['RECORDS_PATH']}day_count_{date_dash_str.replace('-','')}.json", "w"
    ) as json_out:
        json_out.write(json.dumps(records_dict))


@debug
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


# ToDo: Refactor using get_table
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


# ToDo: Refactor using get_table
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
            moth_logger.debug("Today's overlay exists - returning.")
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


def _get_file_update_time(fname: str) -> dt.datetime:
    """ helper function to the updated time of a file """
    return dt.datetime.fromtimestamp(os.path.getmtime(fname))


def get_db_update_time(use_db: bool = False) -> dt.datetime:
    """ Return a datetime.datetime object with the update time of the database
        This only works on some db engines - recent versions of mariadb but not myql
    """
    update_time = None

    if use_db:
        moth_logger.debug("Checking db for last update")
        cnx = mariadb.connect(**sql_config)
        cursor = cnx.cursor()
        cursor.execute(
            "SELECT update_time FROM information_schema.tables "
            f"WHERE TABLE_SCHEMA = 'cold_ash_moths' "
            f"AND table_name = 'moth_records';"
        )
        (update_time,) = cursor.fetchone()
        moth_logger.debug(update_time)
        cursor.close()
        cnx.close()

    if not update_time or not use_db:
        moth_logger.debug("Using last dir update time, ")
        # Find most recent datetime change to the directory and use this.
        update_time = _get_file_update_time(cfg["RECORDS_PATH"])
        moth_logger.debug(update_time)

    return update_time


def get_moth_grid(db):
    """ Returns:
        moth_grid_ccs - string with <style> for moth_grid_container - to set columns
        moth_grid_cells - concatinated lsit of <div> containers to be inserted <grid>
     """

    sql_species_name_by_month_year = """
        SELECT tw.Year, tw.Month, tw.MothName
            FROM (
                SELECT year(Date) Year, month(Date) Month, MothName
                    FROM moth_records
                    WHERE MothName IS NOT NULL
                    GROUP BY Year, Month, MothName
            ) tw
        GROUP BY Year, Month, MothName;"""

    db.execute(sql_species_name_by_month_year)
    data_list = [list(c) for c in db]
    columns = list(db.column_names)
    species_df = pd.DataFrame(data_list, columns=columns).set_index(columns)

    state = {
        (True, True): "Seen",
        (True, False): "Pending",
        (False, True): "New",
        (False, False): "ERROR!!!",
    }

    species_df["V"] = 1
    df = species_df.unstack("Year").loc[dt.date.today().month]["V"]

    cols = 5
    rows = len(df.index) // cols + 1 if len(df.index) % cols else len(df.index) // cols

    cells = [
        f'<div class="{state[(df.loc[mn][:-1].any(), df.loc[mn][-1:].any())]} '
        f"{'shaded' if (((i//rows)+1)+((i%rows)+1))%2 else 'unshaded'}\">{mn}</div>"
        for i, mn in enumerate(df.index)
    ]

    if len(cells) % cols:
        cells.extend([""] * (cols - (len(cells) % cols)))

    # Use css grid to output  a grid rather than a table
    # print(f"No. cells: {len(cells)}")
    # print(f"No. Cols:  {cols}")
    # print(f"No. Rows:  {len(cells)//cols}")

    css = (
        "<style>"
        "   .moth-grid-container {"
        f"    grid-template-rows: {'auto '* int(len(cells)/cols)};"
        "}"
        "</style>"
    )

    return css, "".join(cells)


def generate_monthly_species(cursor):
    """ Called from
        /summary route
        get_summary() """

    moth_logger.debug(f"Creating by monthly chart")
    sql_species_name_by_month_year = """
        SELECT tw.Year, tw.Month, tw.MothName
        FROM (
            SELECT year(Date) Year, month(Date) Month, MothName
                FROM moth_records
                WHERE MothName IS NOT NULL
            GROUP BY Year, Month, MothName
        ) tw
        GROUP BY Year, Month, MothName;"""

    cursor.execute(sql_species_name_by_month_year)
    data_list = [list(c) for c in cursor]
    pre_species_df = pd.DataFrame(data_list, columns=list(cursor.column_names))
    pre_species_df["V"] = 1
    moth_logger.debug(pre_species_df)
    species_df = pre_species_df.set_index(["Month", "Year", "MothName"]).unstack(
        ["Year", "MothName"]
    )["V"]

    x_labels = [dt.date(2019, mn, 1).strftime("%b") for mn in range(1, 13)]

    # Create chart
    this_year = dt.date.today().year
    fig = plt.figure(**plot_dict)
    ax = fig.add_subplot(111)

    ax.bar(
        x_labels,
        species_df.any(axis="columns", level=1).sum(axis="columns").values,
        color="#909090",
        label="All",
    )
    ax.bar(
        x_labels,
        species_df[this_year].sum(axis="columns"),
        width=0.5,
        color="b",
        label=this_year,
    )
    ax.legend()

    plt.savefig(f"{cfg['GRAPH_PATH']}{cfg['BY_MONTH_GRAPH']}")
    plt.close()

    moth_logger.debug(f"Generated species by month graph")


def generate_cummulative_species_graph(cursor):
    """ Called from get_summary """
    today = dt.date.today()

    # Update species graph
    cursor.execute("SELECT year(Date) Year, Date, MothName FROM moth_records;")
    cum_species = pd.DataFrame(
        [list(c) for c in cursor], columns=list(cursor.column_names)
    )
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

    # Mask future dates to avoid plotting a horizontal line to eoy
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


def graph_mothname_v2(mothname):
    catches_df = get_moth_catches(mothname)

    # Test results
    moth_logger.debug(f"Latest date: {catches_df.Date.max()}")
    try:
        moth_logger.debug(
            f"{mothname}.png modified: "
            f'{dt.date.fromtimestamp(os.path.getmtime(f"{GRAPH_PATH}{mothname}.png"))}'
        )
    except FileNotFoundError:
        moth_logger.debug(f"{mothname}.png missing!")

    try:
        if catches_df.Date.max() < dt.date.fromtimestamp(
            os.path.getmtime(f"{GRAPH_PATH}{mothname}.png")
        ):
            moth_logger.debug(f"File is new enough. Not updating {mothname}")
            return
    except FileNotFoundError:
        moth_logger.debug(
            f"Unable to find {GRAPH_PATH}{mothname}.png so will create it."
        )

    # If a moth was caught today the graph will be updated.
    # So find out if the graph is newer than the last database update,
    # if so we don't recreate
    try:
        file_update_time = dt.datetime.fromtimestamp(
            os.path.getmtime(f"{GRAPH_PATH}{mothname}.png")
        )
        moth_logger.debug(f"File: {mothname}.png was updated: {file_update_time}")
        db_update_time = get_db_update_time()
        moth_logger.debug(f"Database:            was updated: {db_update_time}")
        if file_update_time > db_update_time:
            return
    except (FileNotFoundError, TypeError):
        moth_logger.debug("File still not found")

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
    moth_logger.debug(str(plot_dict))
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
app.install(log_to_logger)  # Logs html requests to a file


@app.route("/graphs/<species>")
@debug
def server_graphs(species):
    """ Helper route to return a graph image as a static file. """
    species = species.replace("%20", " ")
    return static_file(f"{species}.png", root=cfg["GRAPH_PATH"])


@app.route("/species")
@debug
def species():
    """ Show  list of moths caught to date. """
    sql_string = """
        SELECT MothName Species, ceil(avg(Total)) "Annual Average"
            FROM (
                SELECT Year(Date) Year, MothName, Sum(MothCount) Total
                    FROM moth_records
                    GROUP BY Year, MothName
            ) yt GROUP BY MothName ORDER BY avg(Total) DESC;"""

    # print(sql_config)
    # cnx = mariadb.connect(**sql_config)
    # cursor = cnx.cursor()

    # cursor.execute(sql_string)
    # data_list = [list(c) for c in cursor]
    # sql_df = pd.DataFrame(data_list, columns=list(cursor.column_names))

    # cursor.close()
    # cnx.close()

    sql_df = get_table(sql_string)

    # Add links
    sql_df["Species"] = sql_df["Species"].map(
        lambda s: f'<a href="/species/{s}">{s}</a>', na_action="ignore"
    )

    return template(
        "species_summary.tpl",
        title="Species Summary",
        species_table=sql_df.to_html(escape=False, index=False, justify="left"),
    )


def get_genus_list():
    """ Show list of moths caught to date. """

    sql_string = """
    SELECT MothGenus Genus, ceil(avg(Count)) `Annual Average` FROM
    (
        SELECT year(Date) Year,  MothGenus,  sum(MothCount) Count
            FROM moth_records INNER JOIN taxonomy
                ON moth_records.MothName = taxonomy.MothName
            GROUP BY Year, MothGenus
    ) gc
    GROUP BY Genus ORDER BY `Annual Average` DESC;"""

    sql_df = get_table(sql_string)

    # Add links
    sql_df["Genus"] = sql_df["Genus"].map(
        lambda s: f'<a href="/genus/{s}">{s}</a>', na_action="ignore"
    )

    return template(
        "species_summary.tpl",
        title="Genus Summary",
        species_table=sql_df.to_html(escape=False, index=False, justify="left"),
    )


def get_family_list():
    """ Show list of moths caught to date. """

    sql_string = """
    SELECT MothFamily Family, ceil(avg(Count)) `Annual Average` FROM
    (
        SELECT year(Date) Year,  MothFamily,  sum(MothCount) Count
            FROM moth_records INNER JOIN taxonomy
                ON moth_records.MothName = taxonomy.MothName
            GROUP BY Year, MothFamily
    ) gc
    GROUP BY Family ORDER BY `Annual Average` DESC;"""

    sql_df = get_table(sql_string)

    # Add links
    sql_df["Family"] = sql_df["Family"].map(
        lambda s: f'<a href="/family/{s}">{s}</a>', na_action="ignore"
    )

    return template(
        "species_summary.tpl",
        title="Family Summary",
        species_table=sql_df.to_html(escape=False, index=False, justify="left"),
    )


@app.route("/genus")
@app.route("/genus/<genus>")
@debug
def get_genus(genus=None):
    """ Show the species in a given genus and graph the aggregation.
        If genus is None then present and ordered list of genus by
        average moth count"""

    if genus is None:
        return get_genus_list()

    sql_string = (
        """
            SELECT Date, moth_records.MothName, MothGenus, sum(MothCount) MothCount
            FROM moth_records INNER JOIN taxonomy
                ON moth_records.MothName = taxonomy.MothName
            WHERE MothGenus LIKE """
        + f'"{genus}" GROUP BY Date;'
    )

    catches_df = get_table(sql_string)
    today = dt.date.today()
    this_year = today.year
    date_year_index = pd.DatetimeIndex(
        pd.date_range(
            start=today.replace(month=1, day=1), end=today.replace(month=12, day=31)
        )
    )

    # Need to average by date
    catches_df["Year"] = catches_df.Date.apply(lambda d: d.timetuple().tm_year)
    catches_df["Date"] = catches_df.Date.apply(lambda d: d.replace(year=this_year))

    table_df = (
        catches_df.drop(["MothName", "MothGenus"], "columns")
        .set_index(["Year", "Date"])
        .unstack("Year")
        .fillna(0)["MothCount"]
        .astype(float)
    )

    table_df["Mean"] = table_df.mean(axis="columns")
    ax = (
        table_df.reindex(date_year_index)
        .fillna(0)[["Mean", this_year]]
        .plot(**plot_dict)
    )
    ax.set_title(f"Genus:{genus}")
    ax.set_ylim(bottom=0)
    plt.savefig(f"{GRAPH_PATH}{genus}.png")
    plt.close()

    return template(
        "genus_summary.tpl", genus=genus, species=catches_df.MothName.unique()
    )


@app.route("/family")
@app.route("/family/<family>")
@debug
def get_family(family=None):
    """ Show the species in a given family and graph the aggregation. """

    if family is None:
        return get_family_list()

    sql_string = (
        """
        SELECT Date, moth_records.MothName, MothFamily, sum(MothCount) MothCount
        FROM moth_records INNER JOIN taxonomy
            ON moth_records.MothName = taxonomy.MothName
        WHERE MothFamily LIKE """
        + f'"{family}" GROUP BY Date;'
    )

    catches_df = get_table(sql_string)
    today = dt.date.today()
    this_year = today.year
    date_year_index = pd.DatetimeIndex(
        pd.date_range(
            start=today.replace(month=1, day=1), end=today.replace(month=12, day=31)
        )
    )

    # Need to average by date
    catches_df["Year"] = catches_df.Date.apply(lambda d: d.timetuple().tm_year)
    catches_df["Date"] = catches_df.Date.apply(lambda d: d.replace(year=this_year))

    table_df = (
        catches_df.drop(["MothName", "MothFamily"], "columns")
        .set_index(["Year", "Date"])
        .unstack("Year")
        .fillna(0)["MothCount"]
        .astype(float)
    )

    table_df["Mean"] = table_df.mean(axis="columns")
    ax = (
        table_df.reindex(date_year_index)
        .fillna(0)[["Mean", this_year]]
        .plot(**plot_dict)
    )
    ax.set_title(f"Family:{family}")
    ax.set_ylim(bottom=0)
    plt.savefig(f"{GRAPH_PATH}{family}.png")
    plt.close()

    return template(
        "family_summary.tpl", family=family, species=catches_df.MothName.unique()
    )


@app.route("/")
@debug
def index():
    """ Landing page for the web site. """
    # Display a landing page
    return template("index.tpl")


@app.route("/static/<filename>")
@debug
def service_static_file(filename):
    """ Help route to return static files. """
    return static_file(f"{filename}", root=cfg["STATIC_PATH"])


@app.route("/survey")
@app.route("/survey/<dash_date_str:re:\\d{4}-\\d{2}-\\d{2}>")
@debug
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

    moth_logger.debug(f"Recent moths:{str(records)}")
    db.close()
    cnx.close()

    return template("survey.tpl", records=records, dash_date_str=dash_date_str)


@app.route("/survey2")
@app.route("/survey2/<dash_date_str:re:\\d{4}-\\d{2}-\\d{2}>")
@debug
def serve_survey2(dash_date_str=None):
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
            # records is a dict whose keys have been managled " " replaced with "_"
            unmangled_records = [
                {"species": k.replace("_", " "), "count": int(v), "recent": 0}
                for k, v in records.items()
            ]
    except FileNotFoundError:
        unmangled_records = []

    moth_logger.debug(f"Recent moths:{str(unmangled_records)}")
    db.close()
    cnx.close()

    return template(
        "vue_survey.tpl", records=unmangled_records, dash_date_str=dash_date_str
    )


@app.route("/summary")
@debug
def get_summary():
    """ Display an overall summary for the Moths web-site. """
    create_graphs = False

    # Determine if summary graph is out of date
    # MariaDB will give the last update time, while MySQL doesn't.
    # So we will use the locally stored records and compare to the timestamp of the file
    try:
        db_update_time = get_db_update_time()
        summary_graph_time = _get_file_update_time(
            f"{cfg['GRAPH_PATH']}{cfg['CUM_SPECIES_GRAPH']}.png"
        )
        create_graphs = db_update_time > summary_graph_time
        moth_logger.debug(
            f"DB updated {db_update_time} since last summary graph update "
            f"{summary_graph_time}. \n"
            f"Updating summary graph"
        )
    except FileNotFoundError:
        create_graphs = True

    cnx = mariadb.connect(**sql_config)
    db = cnx.cursor()
    if create_graphs:
        generate_cummulative_species_graph(db)

        # Update catch diversity graph
        generate_monthly_species(db)

        # Update catch volume graph

    # Generate moth_grid
    grid_css, grid_cells = get_moth_grid(db)
    db.close()
    cnx.close()

    return template(
        "summary.tpl",
        summary_image_file=cfg["GRAPH_PATH"] + cfg["CUM_SPECIES_GRAPH"],
        by_month_image_file=f"{cfg['GRAPH_PATH']}{cfg['BY_MONTH_GRAPH']}",
        moth_grid_css=grid_css,
        moth_grid_cells=grid_cells,
    )


@app.route("/species/<species>")
@debug
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

        t = get_table(f'SELECT * from taxonomy WHERE MothName like "{species}";').iloc[
            0
        ]
        taxo_str = (
            f'<ul style="list-style-type: none;">'
            f'<li><a href="/family/{t.MothFamily}">{t.MothFamily}</a></li>'
            f'<ul style="list-style-type: none;"><li>&#9492;{t.MothSubFamily}</li>'
            f'<ul style="list-style-type: none;">'
            f'<li>&#9492;<a href="/genus/{t.MothGenus}">{t.MothGenus}</a></li>'
            f'<ul style="list-style-type: none;"><li>&#9492;{t.MothSpecies}</li>'
            f"</ul></ul></ul></ul>"
        )

        # Produce a graph of these
        graph_date_overlay()
        graph_mothname_v2(species)

        table_text = all_survey_df[["Date", "MothName", "MothCount"]].to_html(
            escape=False, index=False
        )
        return template(
            "species.tpl", species=species, catches=table_text, taxonomy=taxo_str
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
@debug
def show_latest():
    """ Shows the latest moth catches. """
    # Get a connection to the databe
    cnx = mariadb.connect(**sql_config)

    cursor = cnx.cursor()
    latest_table = show_latest_moths(cursor)
    cnx.close()

    return template("latest.tpl", html_table=latest_table)


@app.post("/handle_survey")
@debug
def survey_handler():
    """ Handler to manage the data returned from the survey sheet. """
    #    today_string = dt.datetime.now()
    date_string = request.forms["dash_date_str"]
    fout_json = (
        cfg["RECORDS_PATH"] + "day_count_" + date_string.replace("-", "") + ".json"
    )

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

    # Store results locally  so when survey sheet is recalled it will auto populate
    with open(fout_json, "w") as fout_js:
        fout_js.write(json.dumps(results_dict))

    # Get a connection to the databe
    cnx = mariadb.connect(**sql_config)
    cursor = cnx.cursor()
    update_moth_database(cursor, date_string, results_dict)
    cnx.close()
    return show_latest()


@app.post("/handle_survey2")
def echo_form():
    date_string = request.forms["dash_date_str"]
    fout_json = (
        cfg["RECORDS_PATH"] + "day_count_" + date_string.replace("-", "") + ".json"
    )

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
            results_dict[moth] = str(specimens).replace(" ", "_")

    # Store results locally  so when survey sheet is recalled it will auto populate
    with open(fout_json, "w") as fout_js:
        fout_js.write(json.dumps(results_dict))

    # Get a connection to the databe
    cnx = mariadb.connect(**sql_config)
    cursor = cnx.cursor()
    update_moth_database(cursor, date_string, results_dict)
    cnx.close()
    return show_latest()


@app.route("/debug")
@debug
def debug_info():
    """ Route showing some debug.
    """
    return [str(route.__dict__) + "</p>" for route in app.routes]


@app.route("/help")
@debug
def survey_help():
    """ Displays a list of links to possible pages """
    output = str()
    output += "<h1>Survey Help Page</h1>"
    output += "<ul>"
    for rte in app.routes:
        label = html.escape(rte.rule)
        output += f"<li><a href={label}>{label}</a></li>"
        docstring = rte.callback.__doc__
        escstring = (
            "None"
            if not docstring
            else html.escape(docstring).replace("\n", "<br />\n")
        )
        output += f"<ul><li><quote>{escstring}</quote></li></ul>"

        moth_logger.debug(rte)
    output += "</ul>"
    return output


if __name__ == "__main__":
    #    app = ProfilerMiddleware(app,
    #                             profile_dir = '/var/www/profile',
    #                             filename_format = "moths_bottle_{time}.prof")

    app.catchall = False
    bottle.run(
        app=app,
        debug=True,
        reloader=True,
        host=cfg["HOST"],
        port=cfg["PORT"],
        server="waitress",
    )

# 20200329 10:07
