#! /usr/bin/python3.7

"""
## Introduction

This Species Survey Software provides a local server for recording and analysing the
data of bio-survey.

### Key features
  * A survey sheet pre-populated with the most likely species to observe
  * Quick addition of new species
  * Rapid graphing analysis of species, genus and family
  * Up-to-date summary for the year and month
  * Quick and easy notification of new species identification
  * Automatic software update
  * Export of month/year data in format ready for upload to iRecord

### Upcoming features
  * Improved Interface to iRecord
  * Improved prediction for survey sheet species based on previous year data
  * Personalisation - colours, fonts, sizes
  * Photo upload and usage on species summary page
  * Food plant information on species summary page

### Science study aims
  * Temperature study
  * Food plant correlation and prediction

### History
     1 Jul 2020
        - On home page set focus to search box when it loads.

    29 Jun 2020
        - Improved /latest including highlights for FFY and New For Trap
        - Fixed date on survey sheet which got lost on ^-back in history
        - Reorder menu & added short cuts for most recent and last updated survey dates
        - Fixed export bug that pulled from wrong taxonomy table
    27 Jun 2020
        - Added a Date picker to the data entry page
    25 Jun 2020
        - db access optimised
        - Fixed bug that prevented simple reuse of graphs
    22 Jun 2020
       - added sessionStorage for data entry
       - improved formating of data entry to highlight new/unused additions.
       - fixed download as year was always 2020
    21 Jun 2020
        - Moth name list is now alphanumerically sorted
        - Moth name list now expires from browser cache in 4hrs
    19 Jun 2020 - Data entry improvements
        - Search list is now punctuation agnostic e.g. White-speck == White speck
        - Duplicates removed from list - fixing a bug that causes list to stick
        - Reduced species persistance in survey sheet to 7 days
        - Allow new species to persist across subsequent days on data entry
        - Combined Common Name and Scientific name on species summary page
    14 Jun 2020 - First pass of species aggregation
    10 Jun 2020 - Started work on aggregating taxon and common names for graphs
    10 Jun 2020 - Changed upload to use Scientific names.
     8 Jun 2020 - Converted to an updatable, iRecord compatible taxonomy database
     6 Jun 2020 - Moving taxo table to irecord taxonomy and adding update abilityq
    25 May 2020 - Tidied data entry screen to provide date na
    24 May 2020 - Tidied Recent catches a little
    24 May 2020 - Improved robustness of get_db_update_time
    24 May 2020 - Fixing monthly column chart for zero months
    12 May 2020 - Started development for iRecord entry
    11 May 2020 - Tidying repos, code and adding this summary to home page
     4 May 2020 - Adding default and local configs for app and sql
     3 May 2020 - Fixed some cases where no data caused a problem
    27 Apr 2020 - Working on new index page to remove autocomplete js
    26 Apr 2020 - Replaced bare metal JS survey sheet with vue
    13 Apr 2020 - Trying to run in a waitress server
     9 Apr 2020 - Fixing Genus and family summaries when nothing  in the current yr
     9 Apr 2020 - removed double import of bottle and added pre and post hooks as debug
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




[1]:/latest

"""

from bottle import Bottle, template, static_file, TEMPLATE_PATH, request, response, run
import pandas as pd
import mysql.connector as mariadb

try:
    from sql_config_local import sql_config
except ModuleNotFoundError:
    from sql_config_default import sql_config
import datetime as dt
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.dates import MonthLocator, DateFormatter
import numpy as np
import logging
import logging.handlers
from functools import wraps
from markdown import markdown

# from werkzeug.middleware.profiler import ProfilerMiddleware
import os
import json
import html
import time
import re

try:
    from app_config_local import app_config as cfg
except ModuleNotFoundError:
    from app_config_default import app_config as cfg
import update_moth_taxonomy

matplotlib.use("Agg")
TEMPLATE_PATH.insert(0, os.getcwd())  # sets the cwd for the bottle templates to work

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

sql_logger = logging.getLogger("sql_logger")
sql_logger.setLevel(logging.DEBUG)
sql_file_handler = logging.handlers.RotatingFileHandler(
    cfg["LOG_PATH"] + "sql_profile.log", maxBytes=1024 * 1024, backupCount=2
)
sql_formatter = logging.Formatter("%(msg)s")
sql_file_handler.setFormatter(sql_formatter)
sql_logger.addHandler(sql_file_handler)


def get_table(sql_query, multi=False):
    """ Creates a pandas DataFrame from a SQL Query"""

    # Establish a connection to the SQL server
    # print(sql_config)
    start = time.time()
    cnx = mariadb.connect(**sql_config)
    cursor = cnx.cursor()

    cursor.execute(sql_query, multi=multi)
    data_list = [list(c) for c in cursor]
    count_df = pd.DataFrame(data_list, columns=list(cursor.column_names))

    cursor.close()
    cnx.close()
    one_line_query = re.sub("[\n\\s]+", " ", sql_query)
    sql_logger.debug(f"{time.time()-start}\t{len(count_df)}\t{one_line_query}")
    return count_df


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


def refresh_manifest(dash_date_str):
    """ Check the javascript manifest.js file is up to date.
        dash_date_str is in the form YYYY-MM-DD"""

    # reject singletons in most recent two catches.
    manifest = (
        get_table(
            f"""SELECT MothName species, Date, SUM(MothCount) recent
            FROM moth_records WHERE
            Date > DATE_ADD(DATE("{dash_date_str}"), INTERVAL -7 DAY) AND
            Date <= DATE("{dash_date_str}") GROUP BY Date, species;"""
        )
        .set_index(["species", "Date"])
        .unstack("Date")
    )

    regular = manifest.count(axis=1) > 1
    last_two_dates = manifest.columns[-2:]
    seen_recently = manifest[last_two_dates].sum(axis=1) > 0
    recent_df = manifest.loc[regular | seen_recently].sum(axis=1).reset_index()
    recent_df.columns = ["species", "recent"]

    # generate javascript file to be sent to browsers
    with open(cfg["STATIC_PATH"] + cfg["MANIFEST_FILE"], "w") as mout:
        mout.write("var recent_moths  = [\n")
        for _, r in recent_df.iterrows():
            mout.write(
                f'    {{species:"{r.species}", recent:{int(r.recent)}, count:0 }},\n'
            )
        mout.write("];")


def update_moth_database(cursor, sql_date_string, dict_records):
    """ Update the mysql server with the latest records
    """

    # touch the records file so we know we have updated the database.
    # This is a workaround as not all databases store when they were updated.
    with open(cfg["RECORDS_PATH"] + cfg["DB_UPDATE_TIME_FILE"], "w"):
        pass

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
    #   columns = []
    records_df = get_table(
        f"""SELECT MothName, MothCount FROM moth_records
            WHERE Date='{date_dash_str}' AND MothName != 'NULL';"""
    )
    records_df["MothName"] = records_df.apply(lambda s: s.replace(" ", "_"))
    records_df.set_index("MothName", inplace=True)
    records_dict = records_df["MothCount"].to_dict()

    moth_logger.debug(records_dict)
    with open(
        f"{cfg['RECORDS_PATH']}day_count_{date_dash_str.replace('-','')}.json", "w"
    ) as json_out:
        json_out.write(json.dumps(records_dict))
    return records_dict


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
    udt = None
    try:
        udt = dt.datetime.fromtimestamp(os.path.getmtime(fname))
        moth_logger.debug(f"Using FILE:{fname} time as db update: {udt}")
    except FileNotFoundError:
        pass
    return udt


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

    if not (update_time and use_db):

        # If we can't use the database to get the update time we must infer it.
        # I'm using a simple file that gets written on a db update.
        db_time_file = cfg["RECORDS_PATH"] + cfg["DB_UPDATE_TIME_FILE"]
        moth_logger.debug(f"Using {db_time_file} to infer database update time, ")
        # Find most recent datetime change to the directory and use this.
        update_time = _get_file_update_time(
            cfg["RECORDS_PATH"] + cfg["DB_UPDATE_TIME_FILE"]
        )

    if update_time is None:
        update_time = dt.datetime.now()
        moth_logger.debug(
            f"Can't determine database update time so using NOW {update_time}!"
        )

    moth_logger.debug(f"Database update time = {update_time}")

    return update_time


def get_moth_grid(db):
    """ Returns:
        moth_grid_ccs - string with <style> for moth_grid_container - to set columns
        moth_grid_cells - concatinated lsit of <div> containers to be inserted <grid>
     """
    cols = 5

    sql_species_name_by_month_year = """
        SELECT tw.Year, tw.Month, tw.MothName
            FROM (
                SELECT year(Date) Year, month(Date) Month, MothName
                    FROM moth_records
                    WHERE MothName IS NOT NULL
                    GROUP BY Year, Month, MothName
            ) tw
        GROUP BY Year, Month, MothName;"""
    # species_df = get_table(sql_species_name_by_month_year)
    # species_df.set_index(list(species_df.columns))

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
    if species_df.empty:
        cells = []
    else:
        df = species_df.unstack("Year").loc[dt.date.today().month]["V"]

        li = len(df.index)
        rows = li // cols + 1 if li % cols else li // cols

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
    this_year = dt.date.today().year

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

    # If the data is empty create a dummy entry
    if pre_species_df.empty:
        species_df = (
            pd.DataFrame(
                {"Month": [1], "Year": [this_year], "MothName": ["Ano"], "V": 0}
            )
            .set_index(["Month", "Year", "MothName"])
            .unstack(["Year", "MothName"])["V"]
        )
    else:
        species_df = pre_species_df.set_index(["Month", "Year", "MothName"]).unstack(
            ["Year", "MothName"]
        )["V"]

    x_labels = [dt.date(2019, mn, 1).strftime("%b") for mn in range(1, 13)]

    # Create chart
    fig = plt.figure(**plot_dict)
    ax = fig.add_subplot(111)

    month_index = list(range(1, 13))
    ax.bar(
        x_labels,
        species_df.any(axis="columns", level=1)
        .sum(axis="columns")
        .reindex(index=month_index, fill_value=0)
        .values,
        color="#909090",
        label="All",
    )
    ax.bar(
        x_labels,
        species_df[this_year]
        .sum(axis="columns")
        .reindex(index=month_index, fill_value=0),
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
    cursor.execute(
        "SELECT year(Date) Year, Date, MothName "
        "FROM moth_records WHERE MothName IS NOT NULL;"
    )
    cum_species = pd.DataFrame(
        [list(c) for c in cursor], columns=list(cursor.column_names)
    )
    cum_species["Catch"] = 1
    cum_species["Date"] = cum_species["Date"].map(
        lambda dd: dd.replace(year=today.year)
    )
    cum_species.set_index(["Year", "Date", "MothName"], inplace=True)
    print("DEBUG")
    print(cum_species)
    cum_species.to_csv("CumSpeciesDebug.csv")
    if cum_species.empty:
        # If dataframe is empty...
        cum_results = pd.DataFrame(
            [0.0], index=pd.Index([today.year], name="Year"), columns=[str(today)]
        )
    else:
        try:
            # The initial groupby is intended to remove duplicate indexes
            cum_results = (
                cum_species.groupby(["Year", "Date", "MothName"])
                .sum()
                .unstack("Date")
                .fillna(method="ffill", axis=1)
                .groupby(by="Year")
                .count()
                .Catch.astype(float)
            )  # Needs to be float for mask to work
        except ValueError:
            # You've probably updated the taxonomy database and this has caused two
            # entries on the same date to merge. This needs fixing/checking
            dups_df = cum_species.groupby(["Year", "Date", "MothName"]).sum()
            moth_logger.error(
                "Finding a duplicate species - probably due to updated "
                "taxonomy database merging species:"
            )
            moth_logger.error(dups_df.loc[dups_df.Catch > 1])
            raise

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
    start = time.time()
    query_str = f"""SELECT mr.Date, mr.MothCount
        FROM (select * from {cfg['TAXONOMY_TABLE']} where MothName = "{mothname}") sp
        JOIN {cfg['TAXONOMY_TABLE']} re
        ON sp.TVK = re.TVK
        JOIN moth_records mr
        ON mr.MothName = re.MothName
        GROUP BY mr.Date;"""
    catches_df = get_table(query_str)
    print(">>> 1st table done: ", time.time() - start)
    # Test results
    moth_logger.debug(f"Most recent catch date: {catches_df.Date.max()}")
    try:
        moth_logger.debug(
            f"{mothname}.png last modified: "
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
    today = dt.date.today()
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

    moth_logger.debug(f"Generating graph: {GRAPH_PATH}{mothname}.png")
    print(">>> 2 decission made: ", time.time() - start)
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
    # moth_logger.debug(str(plot_dict))
    fig = plt.figure(**plot_dict)
    ax = fig.add_subplot(111)
    ax.set_title(mothname)

    # moth_logger.debug(x)
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
    print(">>> 3 graph done: ", time.time() - start)


app = Bottle()
app.install(log_to_logger)  # Logs html requests to a file


@app.route("/graphs/<species>")
def server_graphs(species):
    """ Helper route to return a graph image as a static file. """
    species = species.replace("%20", " ")
    return static_file(f"{species}.png", root=cfg["GRAPH_PATH"])


@app.route("/species_")
def species_():
    """ Show  list of moths caught to date. """
    sql_string = """
        SELECT MothName Species, ceil(avg(Total)) "Annual Average"
            FROM (
                SELECT Year(Date) Year, MothName, Sum(MothCount) Total
                    FROM moth_records
                    GROUP BY Year, MothName
            ) yt GROUP BY MothName ORDER BY avg(Total) DESC;"""
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


def get_used_names(map_tvk2mn, tvk):
    """ Helper function - that returns the common and scientfic names based on
        a map for a specific TVK"""
    t = tvk_entries = map_tvk2mn.loc[tvk]  # Udea olivalis

    scientific_name = ""
    common_name = None
    if isinstance(tvk_entries, pd.Series):
        # Only one name is used
        if t.MothName == t.MothGenus + " " + t.MothSpecies:
            common_name = ""
            scientific_name = t.MothName
        else:
            common_name = t.MothName
            scientific_name = ""
    elif isinstance(tvk_entries, pd.DataFrame):
        # Multiple names used, so filter our scientific
        common_name = ", ".join(
            [
                n.MothName
                for n in tvk_entries.itertuples()
                if n.MothName != n.MothGenus + " " + n.MothSpecies
            ]
        )
        scientific_name = t.iloc[0].MothGenus + " " + t.iloc[0].MothSpecies
    else:
        assert False, "Panic!!!"

    return common_name, scientific_name


@app.route("/species")
def species():
    """ Show  list of moths caught to date. """
    # Get Avg catch per year by TVK
    avg_per_year = get_table(
        f"""
            SELECT TVK, ceil(avg(Total)) "Annual Average"
                FROM (
                    SELECT Year(Date) Year, MothName, TVK,
                    Sum(MothCount) Total, MothGenus, MothSpecies
                        FROM
                        (moth_records JOIN {cfg["TAXONOMY_TABLE"]} USING (MothName))
                        GROUP BY Year, TVK
                ) yt GROUP BY TVK ORDER BY avg(Total) DESC
                ;"""
    )

    # Get a map of all MothNames to TVK
    map_tvk2m = (
        get_table(
            f"""SELECT MothName, TVK, MothGenus, MothSpecies FROM moth_records JOIN
                {cfg["TAXONOMY_TABLE"]} USING (MothName) GROUP BY MothName;"""
        )
        .set_index("TVK")
        .sort_index()
    )

    sql_df = pd.DataFrame(
        [
            [*get_used_names(map_tvk2m, tvk), int(avg)]
            for tvk, avg in zip(avg_per_year.TVK, avg_per_year["Annual Average"])
        ],
        columns=["Species", "Taxon", "Annual Avg."],
    )

    # Add links
    sql_df["Species"] = sql_df["Species"].map(
        lambda s: f'<a href="/species/{s}">{s}</a>', na_action="ignore"
    )
    sql_df["Taxon"] = sql_df["Taxon"].map(
        lambda s: f'<a href="/species/{s}">{s}</a>', na_action="ignore"
    )

    return template(
        "species_summary.tpl",
        title="Species Summary",
        species_table=sql_df.to_html(escape=False, index=False, justify="left"),
    )


def get_genus_list():
    """ Show list of moths caught to date. """

    sql_string = f"""
    SELECT MothGenus Genus, ceil(avg(Count)) `Annual Average` FROM
    (
        SELECT year(Date) Year,  MothGenus,  sum(MothCount) Count
            FROM moth_records INNER JOIN {cfg["TAXONOMY_TABLE"]}
                ON moth_records.MothName = {cfg["TAXONOMY_TABLE"]}.MothName
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

    sql_string = f"""
    SELECT MothFamily Family, ceil(avg(Count)) `Annual Average` FROM
    (
        SELECT year(Date) Year,  MothFamily,  sum(MothCount) Count
            FROM moth_records INNER JOIN {cfg["TAXONOMY_TABLE"]}
                ON moth_records.MothName = {cfg["TAXONOMY_TABLE"]}.MothName
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
def get_genus(genus=None):
    """ Show the species in a given genus and graph the aggregation.
        If genus is None then present and ordered list of genus by
        average moth count"""

    if genus is None:
        return get_genus_list()

    sql_string = (
        f"""
            SELECT Date, moth_records.MothName, MothGenus, sum(MothCount) MothCount
            FROM moth_records INNER JOIN {cfg["TAXONOMY_TABLE"]}
                ON moth_records.MothName = {cfg["TAXONOMY_TABLE"]}.MothName
            WHERE MothGenus LIKE """
        + f'"{genus}" GROUP BY Date;'
    )

    catches_df = get_table(sql_string)
    if catches_df.empty:
        return template("no_records.tpl")

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

    legend = ["Mean"]
    if this_year in catches_df.Year:
        legend += [str(this_year)]

    table_df = (
        catches_df.drop(["MothName", "MothGenus"], "columns")
        .set_index(["Year", "Date"])
        .unstack("Year")
        .fillna(0)["MothCount"]
        .astype(float)
    )

    table_df["Mean"] = table_df.mean(axis="columns")
    ax = table_df.reindex(date_year_index).fillna(0)[legend].plot(**plot_dict)
    ax.set_title(f"Genus:{genus}")
    ax.set_ylim(bottom=0)
    plt.savefig(f"{GRAPH_PATH}{genus}.png")
    plt.close()

    return template(
        "genus_summary.tpl", genus=genus, species=catches_df.MothName.unique()
    )


@app.route("/family")
@app.route("/family/<family>")
def get_family(family=None):
    """ Show the species in a given family and graph the aggregation. """

    if family is None:
        return get_family_list()

    sql_string = (
        f"""
        SELECT Date, moth_records.MothName, MothFamily, sum(MothCount) MothCount
        FROM moth_records INNER JOIN {cfg["TAXONOMY_TABLE"]}
            ON moth_records.MothName = {cfg["TAXONOMY_TABLE"]}.MothName
        WHERE MothFamily LIKE """
        + f'"{family}" GROUP BY Date;'
    )

    catches_df = get_table(sql_string)
    if catches_df.empty:
        return template("no_records.tpl")

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

    legend = ["Mean"]
    if this_year in catches_df.Year:
        legend += [str(this_year)]

    table_df = (
        catches_df.drop(["MothName", "MothFamily"], "columns")
        .set_index(["Year", "Date"])
        .unstack("Year")
        .fillna(0)["MothCount"]
        .astype(float)
    )

    table_df["Mean"] = table_df.mean(axis="columns")
    ax = table_df.reindex(date_year_index).fillna(0)[legend].plot(**plot_dict)
    ax.set_title(f"Family:{family}")
    ax.set_ylim(bottom=0)
    plt.savefig(f"{GRAPH_PATH}{family}.png")
    plt.close()

    return template(
        "family_summary.tpl", family=family, species=catches_df.MothName.unique()
    )


@app.route("/")
def index():
    """ Landing page for the web site. """
    # Display a landing page
    return template("index.tpl", intro=markdown(__doc__))


@app.route("/static/<filename>")
def service_static_file(filename):
    """ Help route to return static files. """
    rsp = static_file(f"{filename}", root=cfg["STATIC_PATH"])
    if filename == "common_names.js":
        # cache common_names for 4hrs
        rsp.set_header("cache-control", f"max-age={4*3600}")

    return rsp


@app.route("/last_survey")
def last_survey():
    """ Identifies the most recent record, and jumps to that survey sheet. """

    latest_record = get_table(
        "SELECT Date, MothName FROM moth_records ORDER by Id DESC LIMIT 1;"
    ).iloc[0]["Date"]
    return serve_survey2(dash_date_str=latest_record.strftime("%Y-%m-%d"))


@app.route("/recent_survey")
def recent_survey():
    """ Identifies the most recent record, and jumps to that survey sheet. """

    latest_record = get_table(
        "SELECT Date, MothName FROM moth_records ORDER by Date DESC LIMIT 1;"
    ).iloc[0]["Date"]
    return serve_survey2(dash_date_str=latest_record.strftime("%Y-%m-%d"))


@app.route("/survey")
@app.route("/survey/<dash_date_str:re:\\d{4}-\\d{2}-\\d{2}>")
def serve_survey2(dash_date_str=None):
    """ Generate a survey sheet to records today's results in. """

    if dash_date_str:
        # generate day_count_YYYYMMDD.json file to later recover the records.
        generate_records_file(None, dash_date_str)
    else:
        dash_date_str = dt.date.today().strftime("%Y-%m-%d")

    # This creates a manifest file which shows possible catches.
    # The template uses this to populate the survey sheet.
    # We could just pass this data to the template.
    refresh_manifest(dash_date_str)

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
    # db.close()
    # cnx.close()

    return template(
        "vue_survey.tpl", records=unmangled_records, dash_date_str=dash_date_str
    )


@app.route("/summary")
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

    except FileNotFoundError:
        create_graphs = True

    cnx = mariadb.connect(**sql_config)
    db = cnx.cursor()
    if create_graphs:
        moth_logger.debug(
            f"DB updated since last summary graph update "
            f"{summary_graph_time}. \n"
            f"Updating summary graph"
        )
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


@app.route("/update_mothnames")
def update_mothnames():
    update_moth_taxonomy.update_mothnames()


@app.route("/species/<species:path>")
def get_species(species):
    """ Generate a summary page for the specified moth species.
        Use % as a wildcard."""
    print(f"Displaying: {species}")
    species = species.replace("%20", " ")
    query_str = f"""SELECT mr.Date, re.MothName, mr.MothCount, re.TVK
        FROM (select * from {cfg['TAXONOMY_TABLE']} where MothName = "{species}") sp
        JOIN {cfg['TAXONOMY_TABLE']} re
            ON sp.TVK = re.TVK
        JOIN moth_records mr
            ON mr.MothName = re.MothName;"""
    all_survey_df = get_table(query_str)

    unique_species = all_survey_df["TVK"].unique()
    if len(unique_species) == 1:
        t = get_table(
            f"""SELECT * from {cfg["TAXONOMY_TABLE"]}
                WHERE MothName like "{species}";"""
        ).iloc[0]
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
    elif len(unique_species) == 0:
        return template("no_records.tpl")
    else:
        # There are multiple species - so provide the choice
        return " ".join(
            [
                f'<a href="/species/{specie}">{specie}</a></p>'
                for specie in unique_species
            ]
        )


def create_species_div(mothname, ffy=False, nft=False):
    """ Called from pd.apply
        Returns a <div> of HTML enclosing mothname and CSS styles
    """
    classes = "nft" if nft else "ffy" if ffy else ""
    tt = ""

    if nft:
        tooltiptext = "New For Trap"
    elif ffy:
        tooltiptext = "First For Year"
    else:
        tooltiptext = ""

    if nft or ffy:
        tt = f'<span class="tooltiptext">{tooltiptext}</span>'
        classes += " tooltip"

    moth_link = f'<a href="/species/{mothname}">{mothname}</a>'
    return f'<div class="{classes}">{moth_link}{tt}</div>'


@app.route("/latest")
def show_latest():
    """ Shows the latest moth catches. """
    # recent_df = get_table(
    #     """SELECT Date, MothName, MothCount FROM moth_records WHERE
    #     Date > DATE_ADD(NOW(), INTERVAL -14 DAY) AND MothName != "NULL";"""
    # )
    recent_df = get_table(
        """SELECT mr.Date, mr.MothName, mr.MothCount FROM moth_records mr
            JOIN
        (SELECT Date from moth_records
            GROUP BY Date
            ORDER BY DATE DESC LIMIT 14) dates
            ON mr.Date = dates.Date ORDER BY Date;"""
    )

    months = [rd.month for rd in recent_df.Date.unique()]
    month_count = {mm: months.count(mm) for mm in set(months)}
    biggest_month = sorted(month_count.items(), key=lambda kv: kv[1], reverse=True)[0][
        0
    ]
    recent_df["Month"] = recent_df["Date"].apply(
        lambda dd: f"{dd.strftime('%b %Y' if dd.month == biggest_month else '%b')}"
    )

    # Find New For Trap and First For Year
    nft = get_table(
        f"""SELECT MothName, Date from moth_records
        JOIN (
        SELECT MothName, TVK from {cfg["TAXONOMY_TABLE"]}) it USING (MothName)
        GROUP BY TVK Having COUNT(TVK) = 1 AND Date = Date(NOW());"""
    ).MothName.to_list()
    print(nft)

    ffy = get_table(
        f"""SELECT MothName, Date FROM
        moth_records
        JOIN (
        SELECT MothName, TVK from {cfg["TAXONOMY_TABLE"]}) it USING (MothName)
        WHERE YEAR(Date) = YEAR(NOW())
        GROUP BY TVK Having COUNT(TVK) = 1 AND Date = Date(NOW());"""
    ).MothName.to_list()
    print(ffy)

    recent_df["Species"] = recent_df["MothName"].apply(
        lambda mn: create_species_div(mn, ffy=mn in ffy, nft=mn in nft)
    )
    recent_df["Date"] = recent_df["Date"].apply(
        lambda dd: f'<a href="/survey/{dd}">{dd.strftime("%d")}</a>'
    )
    recent_df.set_index(["Month", "Date", "MothName", "Species"], inplace=True)

    latest_table = (
        recent_df["MothCount"]
        .unstack(["Month", "Date"])
        .fillna("")
        .droplevel("MothName")
    )

    return template(
        "latest.tpl",
        html_table=latest_table.to_html(escape=False, classes="latest_table"),
    )


@app.post("/handle_survey")
def survey_handler():
    """ Handler to manage the data returned from the survey sheet. """
    #    today_string = dt.datetime.now()
    date_string = request.forms["dash_date_str"]
    fout_json = (
        cfg["RECORDS_PATH"] + "day_count_" + date_string.replace("-", "") + ".json"
    )

    rs = []
    results_dict = {}
    for moth in request.forms.keys():
        if moth == "dash_date_str":
            continue
        specimens = request.forms.get(
            moth, default=0, index=0, type=int
        )  # leave result as string
        if specimens:
            rs.append(f"<p><strong>{moth}</strong>      {specimens}</p>")
            # replace spaces for backward compate
            # TO DO - can we remove name mangling
            results_dict[moth] = str(specimens).replace(" ", "_")

    # Store results locally  so when survey sheet is recalled it will auto populate
    # This probably isn't really required as we can access the SQL quickly
    with open(fout_json, "w") as fout_js:
        moth_logger.debug(f"Updating {fout_json} file")
        moth_logger.debug(results_dict)
        fout_js.write(json.dumps(results_dict))

    # Get a connection to the databe
    cnx = mariadb.connect(**sql_config)
    cursor = cnx.cursor()
    update_moth_database(cursor, date_string, results_dict)
    cnx.close()

    # If the date string is today-return recent catches page,
    # otherwise show data entry for the next day
    page_date = dt.datetime.strptime(date_string, "%Y-%m-%d")
    if page_date.date() == dt.date.today():
        rsp = show_latest()
    else:
        rsp = serve_survey2((page_date + dt.timedelta(days=1)).strftime("%Y-%m-%d"))
    # Set the a cookie "delete_cache_date" to remove local stored data which woul
    # over write data if edited on another machine. So we want to delete this
    # data on a successful submission. The tpl files must handle this and clear
    # the cookie. This won't handle stale data on one machine from overwriting update
    # but that is an unlikely edge case.
    response.set_header("set-cookie", f"delete_cache_date={date_string}")
    return rsp


@app.route("/debug")
def debug_info():
    """ Route showing some debug.
    """
    return [str(route.__dict__) + "</p>" for route in app.routes]


@app.route("/download/<dl_year>")
@app.route("/download/<dl_year>/<dl_month>")
def export_data(dl_year, dl_month=None):
    """ This function generate the csv to be exported in a format
        compatible with iRecord https://www.brc.ac.uk/irecord/import-records
    """

    month_option = f" AND Month(Date)={dl_month}" if dl_month else ""
    query_string = f"""SELECT mr.Date, CONCAT(mt.MothGenus, " ", mt.MothSpecies) Species,
        mr.MothCount Quantity,
        CONCAT("Lamp used: ",mr.Lamp, "\nCommon Name: ", mt.MothName) Comment
        FROM (select * FROM moth_records WHERE Year(Date)={dl_year} {month_option}) mr
        JOIN {cfg["TAXONOMY_TABLE"]} mt ON mr.MothName=mt.MothName;"""

    moth_logger.debug(query_string)
    export_data = get_table(query_string)

    # Add data for iRecord
    export_data["GridRef"] = "SU5120569500"
    export_data["Recorder Name"] = "Gareth Scourfield"

    return template(export_data.loc[export_data["Quantity"] != 0].to_csv(index=False))


@app.route("/export")
def export_page():
    """ Page for exporting moth records in a format compatible with iRecord
        Columns: Species, Site Name, Site Name, Grid Ref, Date.
    """

    # Determine oldest record
    earliest_record = get_table("SELECT MIN(Date) Earliest FROM moth_records;")[
        "Earliest"
    ][0]
    moth_logger.debug(">>>>", earliest_record.year)
    return template(
        "export", e_year=earliest_record.year, e_month=earliest_record.month
    )


@app.route("/help")
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

    # Check whether database needs an update
    update_moth_taxonomy.update_table_moth_taxonomy()

    # Run server
    run(
        app=app,
        debug=True,
        reloader=True,
        host=cfg["HOST"],
        port=cfg["PORT"],
        server="waitress",
    )
