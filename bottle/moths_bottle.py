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
    24 Jul 2022 - Add support for sqlite3
    30 Jun 2022 - Fixed a bug exposed by latest pandas
    31 Jan 2021 - Pulled 'Site name' out of comment into its own column for export
    17 Jan 2021 - Fixed graph x-axis to use a leap year 2000 as base
    29 Sep 2020 - Implementing a cache on the graphs
    27 Sep 2020 - Finshed adding plotly summary is no 24s.
    14 Sep 2020 - Started adding plotly for summary (initially 35s, subsequenc 4s)
    12 Sep 2020 - Fixed over eager default on options page
     6 Sep 2020 - /latest no longer highlights synonyms as FFY/NFT if TVK seen before
     6 Sep 2020 - Fixed some bugs on /latest page that showed nfy/fft in error
    31 Aug 2020 - Refactored "/latest" page to use Vue
    18 Aug 2020 - Started work to improve latest page.
    15 Aug 2020 - Maked options apply immediately, and fixing NULL record issue
    14 Aug 2020 - Make opt default sticky for  browser iff it is in the option list
    12 Aug 2020 - using JSON obj to pass captured moths to survey sheet
    11 Aug 2020 - disabled lastpass for Survey page, and reset count colours as needed
    10 Aug 2020 - ghi0020: Added options for Recorder, Lamp and Location
    1 Jul 2020
        - On home page set focus to search box when it loads
        - Latest page highlight persist while first is in table - not just latest date
        - Now includes all species in drop down list, and jumps to species that exist
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


"""
import os
import json
import html
import time
import re
import datetime as dt
import logging
import logging.handlers
from functools import wraps, lru_cache
from markdown import markdown
import sqlite3

import numpy as np
from bottle import Bottle, template, static_file, TEMPLATE_PATH, request, response, run
import pandas as pd
import mysql.connector as mariadb

# from werkzeug.middleware.profiler import ProfilerMiddleware

try:
    import plotly.graph_objects as go
except ModuleNotFoundError:
    try:
        import subprocess
        import sys

        def install(package):
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

        install("plotly")
        import plotly.graph_objects as go
    except ModuleNotFoundError:
        print("Still can't import plotly!!!")

try:
    from sql_config_local import sql_config
except ModuleNotFoundError:
    from sql_config_default import sql_config
try:
    from app_config_local import app_config as cfg
except ModuleNotFoundError:
    from app_config_default import app_config as cfg
import update_moth_taxonomy

pd.options.plotting.backend = "plotly"
BASE_YEAR = 2000  # Needs to be a leap year so we can map all days onto the same graph

# Set up plotly theme
this_year = dt.date.today().year
line_layout = go.Layout(
    autosize=False,
    width=1000,
    height=450,
    title=dict(x=0, font=dict(size=32)),
    yaxis=dict(rangemode="tozero", title={"text": ""}),
    xaxis=dict(
        dtick="M1",
        tickformat="%b",
        range=[f"{BASE_YEAR}-01-01", "f{BASE_YEAR}-12-31"],
        title={"text": ""},
    ),
    plot_bgcolor="#f8f8f8",
)

TEMPLATE_PATH.insert(0, os.getcwd())  # sets the cwd for the bottle templates to work

# Override the pandas' max display width to prevent to_html truncating cols
pd.set_option("display.max_colwidth", None)

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
    return update_moth_taxonomy.get_table(sql_query)

#    # Establish a connection to the SQL server
#    start = time.time()
##    cnx = mariadb.connect(**sql_config)
#    cnx = update_moth_taxonomy.get_db_connection()
#    cursor = cnx.cursor()
#
#    if cfg["USE_SQLITE"]:
#        cursor.execute(sql_query)
#        print("===", cursor.description)
#        table = cfg["TAXONOMY_TABLE"]
#        columns = [
#            n[0] 
#            for n in cursor.execute(f'SELECT name FROM PRAGMA_TABLE_INFO("{sql_query}");')
#            ]
#        print(">>>", columns)
# #       columns = [
# #           n[0] 
# #           for n in cursor.execute(f'SELECT name FROM PRAGMA_TABLE_INFO("irecord_taxonomy");')
# #           ]
# #       print(columns)
#
#    else:
#        cursor.execute(sql_query, multi=multi)
#        columns =list(cursor.column_names)
# 
#    data_list = [list(c) for c in cursor]
#    count_df = pd.DataFrame(data_list, columns=columns)
#
#    cursor.close()
#    cnx.close()
#    one_line_query = re.sub("[\n\\s]+", " ", sql_query)
#    sql_logger.debug(f"{time.time()-start}\t{len(count_df)}\t{one_line_query}")
#    return count_df


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
    """ The manifest.js file is a list of the most likely moths to be caught
        along with the number of recently caught speciments."""

    if cfg["USE_SQLITE"]:
        sql_query = f"""SELECT MothName species, Date, SUM(MothCount) recent
            FROM moth_records WHERE
            MothName != "None" AND
            Date > DATE("{dash_date_str}", "-7 DAYS") AND
            Date <= DATE("{dash_date_str}") GROUP BY Date, species;"""
    else:
        sql_query = f"""SELECT MothName species, Date, SUM(MothCount) recent
            FROM moth_records WHERE
            MothName != "None" AND
            Date > DATE_ADD(DATE("{dash_date_str}"), INTERVAL -7 DAY) AND
            Date <= DATE("{dash_date_str}") GROUP BY Date, species;"""

    # reject singletons in most recent two catches.
    manifest = (
        get_table(sql_query
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
            '("{}", "{}", {}, "{}", "{}", "{}")'.format(
                sql_date_string,
                k.replace("_", " "),
                v["count"],
                v["location"],
                v["recorder"],
                v["trap"],
            )
            for k, v in dict_records.items()
            if k != "nan" and v["count"] > 0
        ]

        ins_string = ", ".join(ins_list)
        cursor.execute(
            "INSERT INTO moth_records "
            "(Date, MothName, MothCount, Location, Recorder, Trap) VALUES {};".format(
                ins_string
            )
        )


def generate_records_file(cursor, date_dash_str):
    """ Ensure the records file cfg['RECORD_PATH'] exists
        This file contains the {moth(with underscords): count:str} dict in json form
    """
    #   columns = []
    records_df = get_table(
        f"""SELECT MothName AS species, MothCount AS count,
            Location AS location, Recorder AS recorder, Trap AS trap FROM moth_records
            WHERE Date='{date_dash_str}' AND MothName != 'NULL';"""
    )
    print(records_df)
    records_df["species"] = records_df.species.apply(lambda s: s.replace(" ", "_"))
    records_df.set_index("species", inplace=True)
    records_dict = records_df.to_dict(orient="index")

    moth_logger.debug(records_dict)
    with open(
        f"{cfg['RECORDS_PATH']}day_count_{date_dash_str.replace('-','')}.json", "w"
    ) as json_out:
        json_out.write(json.dumps(records_dict))
    return records_dict


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
#        cnx = mariadb.connect(**sql_config)
        cnx = update_moth_taxonomy.get_db_connection()
        cursor = cnx.cursor()
        cursor.execute(
            "SELECT update_time FROM information_schema.tables "
            "WHERE TABLE_SCHEMA = 'cold_ash_moths' "
            "AND table_name = 'moth_records';"
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


def get_moth_grid():
    """ Provides a grid of species that have been caught in this month compared with
        previous years.
        Returns:
        moth_grid_ccs - string with <style> for moth_grid_container - to set columns
        moth_grid_cells - concatinated list of <div> containers to be inserted <grid>
     """
    current_month = dt.date.today().month
    cols = 5

    sql_species_name_by_month_year = f"""
        SELECT tw.Year, tw.Month, tw.MothName
            FROM (
                SELECT year(Date) Year, month(Date) Month, MothName
                    FROM moth_records
                    WHERE MothName IS NOT NULL AND month(Date) = {current_month}
                    GROUP BY Year, Month, MothName
            ) tw
        GROUP BY Year, Month, MothName;"""

    species_df = get_table(sql_species_name_by_month_year)

    state = {
        (True, True): "Seen",
        (True, False): "Pending",
        (False, True): "New",
        (False, False): "ERROR!!!",
    }

    if species_df.empty:
        cells = []
    else:
        species_df.set_index(species_df.columns.to_list(), inplace=True)
        species_df["V"] = 1
        df = species_df.unstack("Year").loc[current_month]["V"]

        li = len(df.index)
        rows = li // cols + 1 if li % cols else li // cols

        cells = [
            f'<div class="{state[(df.loc[mn][:-1].any(), df.loc[mn][-1:].any())]} '
            f"{'shaded' if (((i//rows)+1)+((i%rows)+1))%2 else 'unshaded'}\">{mn}</div>"
            for i, mn in enumerate(df.index)
        ]

    if len(cells) % cols:
        cells.extend([""] * (cols - (len(cells) % cols)))

    css = (
        "<style>"
        "   .moth-grid-container {"
        f"    grid-template-rows: {'auto '* int(len(cells)/cols)};"
        "}"
        "</style>"
    )

    return css, "".join(cells)


def generate_monthly_species(cursor=None):
    """ Called from
        /summary route
        get_summary() """
    this_year = dt.date.today().year

    moth_logger.debug("Creating by monthly chart")
    pre_species_df = get_table(
        """
        SELECT tw.Year, tw.Month, tw.MothName
        FROM (
            SELECT year(Date) Year, month(Date) Month, MothName
                FROM moth_records
                WHERE MothName IS NOT NULL
            GROUP BY Year, Month, MothName
        ) tw
        GROUP BY Year, Month, MothName;"""
    )

    if pre_species_df.empty:
        pre_species_df = pd.DataFrame(
            {"Month": range(1, 13), "Year": [this_year] * 12, "MothName": [None] * 12}
        ).set_index("Month")

    # Count each species per Month-Year
    g = pre_species_df.groupby(["Year", "Month"])
    by_month_df = g.count().unstack("Year")["MothName"]
    by_month_df = by_month_df.reindex(range(1, 13), fill_value=0)

    # Find all species caught in a month regardless of year
    gm = pre_species_df.groupby(["Month", "MothName"])
    by_all_df = gm.count().unstack("MothName").count(axis="columns")

    x_labels = [dt.date(2019, mn, 1).strftime("%b") for mn in range(1, 13)]

    # Create chart
    fig = go.Figure()
    fig.add_trace(go.Bar(x=x_labels, y=by_all_df, marker_color="#909090", name="All"))
    if this_year in by_month_df.columns:
        fig.add_trace(
            go.Bar(
                x=x_labels,
                y=by_month_df[this_year],
                width=0.5,
                marker_color="blue",
                name=this_year,
            )
        )
    fig.update_layout(barmode="overlay")
    fig.layout.legend.x = 0.99
    fig.layout.legend.y = 0.98
    fig.layout.legend.xanchor = "right"
    fig.layout.width = 1000
    fig.layout.height = 450
    fig.update_xaxes(title=None)
    fig.update_yaxes(title=None)

    return fig.to_json()


def generate_cummulative_species_graph(cursor=None):
    """ Called from get_summary """
    today = dt.date.today()

    # Update species graph
    cum_species = get_table(
        "SELECT year(Date) Year, Date, MothName "
        "FROM moth_records WHERE MothName IS NOT NULL;"
    )

    cum_species["Catch"] = 1
    cum_species["Date"] = cum_species["Date"].map(lambda dd: dd.replace(year=BASE_YEAR))
    cum_species.set_index(["Year", "Date", "MothName"], inplace=True)

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
    if today.year in cum_results.index:
        cum_results.loc[today.year].mask(
            cum_results.columns > str(today.replace(year=BASE_YEAR)),
            other=np.NaN,
            inplace=True,
        )
    # Generate cumulative species graph
    # Create chart
    fig = cum_results.transpose().plot()
    fig.update_layout(title="Cummulative Species")
    fig.layout.legend.x = 0.01
    fig.layout.legend.y = 0.98
    fig.layout.legend.xanchor = "left"
    fig.update_layout(line_layout)  # line_graph_theme
    return fig.to_json()


def graph_mothname_v3(mothname):
    """ Using plotly return the json data for a browser rendered graph
    """

    catches_df = get_table(
        f"""SELECT mr.Date, mr.MothCount
        FROM (select * from {cfg['TAXONOMY_TABLE']} where MothName = "{mothname}") sp
        JOIN {cfg['TAXONOMY_TABLE']} re
        ON sp.TVK = re.TVK
        JOIN moth_records mr
        ON mr.MothName = re.MothName
        GROUP BY mr.Date;"""
    )

    today = dt.date.today()
    nyd = today.replace(month=1, day=1)
    nye = today.replace(month=12, day=31)

    date_year_index = pd.DatetimeIndex(
        pd.date_range(
            start=nyd.replace(year=BASE_YEAR), end=nye.replace(year=BASE_YEAR)
        )
    )

    this_year_df = catches_df[catches_df["Date"] >= nyd]
    this_year_df["Date"] = this_year_df["Date"].map(lambda e: e.replace(year=BASE_YEAR))
    this_year_df = (
        this_year_df.set_index("Date")
        .reindex(date_year_index, fill_value=0)
        .reset_index()
    )

    catches_df["Date"] = catches_df["Date"].map(lambda e: e.replace(year=BASE_YEAR))
    flattened_df = catches_df.groupby("Date").mean()
    all_catches_df = flattened_df.reindex(date_year_index, fill_value=0).reset_index()

    # Render with plotly
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=all_catches_df["index"],
            y=all_catches_df.MothCount,
            mode="lines",
            name="Average",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=this_year_df["index"],
            y=this_year_df.MothCount,
            mode="lines",
            name=f"{today.year}",
        )
    )
    fig.add_shape(
        # Line Vertical
        dict(
            type="line",
            x0=today.replace(year=BASE_YEAR),
            y0=0,
            x1=today.replace(year=BASE_YEAR),
            y1=1,
            yref="paper",
            line=dict(color="Black", width=3, dash="dot"),
        )
    )

    fig.layout.title = mothname
    fig.layout.legend.x = 0.99
    fig.layout.legend.y = 0.98
    fig.layout.legend.xanchor = "right"
    fig.update_layout(line_layout)

    return fig.to_json()


app = Bottle()
app.install(log_to_logger)  # Logs html requests to a file


@app.route("/graphs/<species>")
def server_graphs(species):
    """ Helper route to return a graph image as a static file. """
    species = species.replace("%20", " ")
    return static_file(f"{species}.png", root=cfg["GRAPH_PATH"])


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
            n.MothName
            for n in tvk_entries.itertuples()
            if n.MothName != n.MothGenus + " " + n.MothSpecies
        )
        scientific_name = t.iloc[0].MothGenus + " " + t.iloc[0].MothSpecies
    else:
        assert False, "Panic!!!"

    return common_name, scientific_name


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
            start=today.replace(year=BASE_YEAR, month=1, day=1),
            end=today.replace(year=BASE_YEAR, month=12, day=31),
        )
    )

    # Need to average by date
    catches_df["Year"] = catches_df.Date.apply(lambda d: d.timetuple().tm_year)
    catches_df["Date"] = catches_df.Date.apply(lambda d: d.replace(year=BASE_YEAR))

    legend = ["Mean"]
    if this_year in catches_df.Year.unique():
        legend += [this_year]

    table_df = (
        catches_df.drop(["MothName", "MothGenus"], "columns")
        .set_index(["Year", "Date"])
        .unstack("Year")
        .fillna(0)["MothCount"]
        .astype(float)
    )

    table_df["Mean"] = table_df.mean(axis="columns")
    fig = table_df.reindex(date_year_index).fillna(0)[legend].plot()
    fig.add_shape(
        # Line Vertical
        dict(
            type="line",
            x0=today.replace(year=BASE_YEAR),
            y0=0,
            x1=today.replace(year=BASE_YEAR),
            y1=1,
            yref="paper",
            line=dict(color="Black", width=3, dash="dot"),
        )
    )
    fig.update_xaxes(
        ticklabelmode="period",
        dtick="M1",
        tickformat="%b",
        range=[f"{BASE_YEAR}-01-01", f"{BASE_YEAR}-12-31"],
    )
    fig.layout.title = genus
    fig.update_layout(line_layout)

    return template(
        "genus_summary.tpl",
        genus=genus,
        species=catches_df.MothName.unique(),
        gg=fig.to_json(),
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
            start=today.replace(year=BASE_YEAR, month=1, day=1),
            end=today.replace(year=BASE_YEAR, month=12, day=31),
        )
    )

    # Need to average by date
    catches_df["Year"] = catches_df.Date.apply(lambda d: d.timetuple().tm_year)
    catches_df["Date"] = catches_df.Date.apply(lambda d: d.replace(year=BASE_YEAR))

    legend = ["Mean"]
    if this_year in catches_df.Year.unique():
        legend += [this_year]

    table_df = (
        catches_df.drop(["MothName", "MothFamily"], "columns")
        .set_index(["Year", "Date"])
        .unstack("Year")
        .fillna(0)["MothCount"]
        .astype(float)
    )

    table_df["Mean"] = table_df.mean(axis="columns")
    fig = table_df.reindex(date_year_index).fillna(0)[legend].plot()
    fig.add_shape(
        # Line Vertical
        dict(
            type="line",
            x0=today.replace(year=BASE_YEAR),
            y0=0,
            x1=today.replace(year=BASE_YEAR),
            y1=1,
            yref="paper",
            line=dict(color="Black", width=3, dash="dot"),
        )
    )
    fig.update_xaxes(
        ticklabelmode="period",
        dtick="M1",
        tickformat="%b",
        range=[f"{BASE_YEAR}-01-01", f"{BASE_YEAR}-12-31"],
    )
    fig.layout.title = family
    fig.update_layout(line_layout)

    return template(
        "family_summary.tpl",
        family=family,
        species=catches_df.MothName.unique(),
        fg=fig.to_json(),
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

    if not dash_date_str:
        # Create today's dash_date_str
        dash_date_str = dt.date.today().strftime("%Y-%m-%d")

    # generate day_count_YYYYMMDD.json file to later recover the records.
    generate_records_file(None, dash_date_str)

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
                {
                    "species": k.replace("_", " "),
                    "count": int(v["count"]),
                    "recent": 0,
                    "location": v["location"],
                    "recorder": v["recorder"],
                    "trap": v["trap"],
                }
                for k, v in records.items()
            ]
    #    except FileNotFoundError:
    except IndexError:
        unmangled_records = []

    moth_logger.debug(f"Recent moths:{str(unmangled_records)}")

    recorder_list = get_table("SELECT * from recorders_list;")["Recorder"].to_list()
    trap_list = get_table("SELECT * from traps_list;")["Trap"].to_list()
    location_list = get_table("SELECT Name from locations_list;")["Name"].to_list()

    return template(
        "vue_survey.tpl",
        records=json.dumps(unmangled_records),
        dash_date_str=dash_date_str,
        default_location=update_moth_taxonomy.get_column_default("Location"),
        location_list=location_list,
        default_trap=update_moth_taxonomy.get_column_default("Trap"),
        trap_list=trap_list,
        default_recorder=update_moth_taxonomy.get_column_default("Recorder"),
        recorder_list=recorder_list,
    )


@app.route("/summary")
@lru_cache(maxsize=3)
def get_summary():
    """ Display an overall summary for the Moths web-site. """

    csg = generate_cummulative_species_graph()
    bmg = generate_monthly_species()

    # Generate moth_grid
    grid_css, grid_cells = get_moth_grid()

    return template(
        "summary.tpl",
        summary_graph_json=csg,
        summary_image_file=cfg["GRAPH_PATH"] + cfg["CUM_SPECIES_GRAPH"],
        by_month_graph_json=bmg,
        by_month_image_file=f"{cfg['GRAPH_PATH']}{cfg['BY_MONTH_GRAPH']}",
        moth_grid_css=grid_css,
        moth_grid_cells=grid_cells,
    )


@app.route("/update_mothnames")
def update_mothnames():
    update_moth_taxonomy.update_mothnames()


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


@app.route("/species/<species:path>")
@lru_cache(maxsize=16)
def get_pspecies(species):
    """ Generate a summary page for the specified moth species.
        Use % as a wildcard."""

    species = species.replace("%20", " ")
    query_str = f"""SELECT mr.Date, re.MothName, mr.MothCount, re.TVK
        FROM (select * from {cfg['TAXONOMY_TABLE']} where MothName = "{species}") sp
        JOIN {cfg['TAXONOMY_TABLE']} re
            ON sp.TVK = re.TVK
        JOIN moth_records mr
            ON mr.MothName = re.MothName
        ORDER BY mr.Date;"""
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
        graph_json = graph_mothname_v3(species)
        table_text = all_survey_df[["Date", "MothName", "MothCount"]].to_html(
            escape=False, index=False
        )
        return template(
            "pspecies.tpl",
            species=species,
            catches=table_text,
            taxonomy=taxo_str,
            plotly_data=graph_json,
        )
    elif len(unique_species) == 0:
        return template("no_records.tpl")
    else:
        # There are multiple species - so provide the choice
        return " ".join(
            f'<a href="/species/{specie}">{specie}</a></p>' for specie in unique_species
        )


@app.route("/latest")
def show_latest():
    """ Table showing the latest moths - need to consider options
        e.g. location (allow multiple selections)
    """

    # Get the records for last 14 dates trapped
    recent_df = get_table(
        """SELECT mr.Date, mr.MothName, mr.MothCount, TVK FROM moth_records mr
            JOIN irecord_taxonomy USING (MothName)
            JOIN (SELECT Date from moth_records
            GROUP BY Date
            ORDER BY Date DESC LIMIT 14) dates
            USING (Date) ORDER BY Date;"""
    )

    earliest_table_date = min(recent_df.Date)

    seen_before = get_table(
        f"""SELECT MothName, YEAR(Max(Date)) Year, TVK FROM
                (SELECT * FROM moth_records WHERE
                    Date < Date("{earliest_table_date}") ) mr
                JOIN
                {cfg["TAXONOMY_TABLE"]} USING (MothName)
        GROUP BY MothName;"""
    )

    not_nft_tvk = seen_before.TVK.to_list()
    not_ffy_tvk = seen_before[seen_before.Year == dt.date.today().year].TVK.to_list()

    table_moths = dict(zip(recent_df.MothName, recent_df.TVK))
    nft = [mn for mn, tvk in table_moths.items() if tvk not in not_nft_tvk]
    ffy = [
        mn
        for mn, tvk in table_moths.items()
        if tvk not in not_ffy_tvk and mn not in nft
    ]

    recent_df["Date"] = recent_df["Date"].apply(lambda dd: dd.strftime("%Y-%m-%d"))
    recent_df["Species"] = recent_df["MothName"]
    recent_df.set_index(["Date", "MothName", "Species"], inplace=True)

    latest_table = (
        recent_df["MothCount"].unstack(["Date"]).fillna("").droplevel("MothName")
    )

    return template(
        "latest2.tpl",
        records=latest_table.to_json(orient="split"),
        nft=json.dumps(list(nft)),
        ffy=json.dumps(list(ffy)),
    )


@app.post("/handle_survey")
def survey_handler():
    """ Handler to manage the data returned from the survey sheet. """

    date_string = request.forms["dash_date_str"]
    default_recorder = request.forms.get("option_Recorder") or "NULL"
    default_trap = request.forms.get("option_Trap") or "NULL"
    default_location = request.forms.get("option_Location") or "NULL"

    fout_json = (
        cfg["RECORDS_PATH"] + "day_count_" + date_string.replace("-", "") + ".json"
    )

    results_dict = {}
    for moth in request.forms.keys():
        if moth in [
            "dash_date_str",
            "option_Recorder",
            "option_Location",
            "option_Trap",
        ]:
            continue
        specimens = json.loads((request.forms.get(moth)))
        if not isinstance(specimens["count"], int):
            continue
        if specimens["count"] <= 0:
            continue

        specimens["recorder"] = specimens["recorder"] or default_recorder
        specimens["trap"] = specimens["trap"] or default_trap
        specimens["location"] = specimens["location"] or default_location
        results_dict[moth] = specimens

    # Store results locally  so when survey sheet is recalled it will auto populate
    # This probably isn't really required as we can access the SQL quickly
    with open(fout_json, "w") as fout_js:
        moth_logger.debug(f"Updating {fout_json} file")
        moth_logger.debug(results_dict)
        fout_js.write(json.dumps(results_dict))

    # Get a connection to the databe
#    cnx = mariadb.connect(**sql_config)
    cnx = update_moth_taxonomy.get_db_connection()
    cursor = cnx.cursor()
    update_moth_database(cursor, date_string, results_dict)
    cnx.close()

    # Clear species cache
    get_pspecies.cache_clear()
    get_summary.cache_clear()

    # If the date string is today-return recent catches page,
    # otherwise show data entry for the next day
    page_date = dt.datetime.strptime(date_string, "%Y-%m-%d")
    if page_date.date() == dt.date.today():
        rsp = show_latest()
    else:
        rsp = serve_survey2((page_date + dt.timedelta(days=1)).strftime("%Y-%m-%d"))
    # Set the a cookie "delete_cache_date" to remove local stored data which would
    # overwrite data if edited on another machine. So we want to delete this
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
        mr.MothCount Quantity, ll.OSGB_Grid GridRef, mr.Recorder "Recorder Name",
        mr.Location "Site name",
        CONCAT("Lamp Trap: ", mr.Trap, "\nCommon Name: ", mt.MothName) Comment
        FROM (select * FROM moth_records WHERE Year(Date)={dl_year} {month_option}) mr
        JOIN (SELECT * FROM {cfg["TAXONOMY_TABLE"]}) mt ON mr.MothName=mt.MothName
        JOIN (SELECT * FROM locations_list) ll ON ll.Name=mr.Location;"""

    moth_logger.debug(query_string)
    export_data = get_table(query_string)
    export_data["Stage"] = "Adult"  # Currently we only survey by adults
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


@app.route("/options")
def config_options():
    """ Configuration page for options
    """

    recorder_list = get_table("SELECT * from recorders_list;")
    trap_list = get_table("SELECT * from traps_list;")
    location_list = get_table("SELECT * from locations_list;")

    def_location = update_moth_taxonomy.get_column_default("Location")
    def_recorder = update_moth_taxonomy.get_column_default("Recorder")
    def_trap = update_moth_taxonomy.get_column_default("Trap")

    return template(
        "options",
        location_template=location_list.columns.to_list(),
        location_list=location_list.to_dict(orient="records"),
        default_location=def_location,
        recorder_template=recorder_list.columns.to_list(),
        recorder_list=recorder_list.to_dict(orient="records"),
        default_recorder=def_recorder,
        trap_template=trap_list.columns.to_list(),
        trap_list=trap_list.to_dict(orient="records"),
        default_trap=def_trap,
    )


@app.post("/add_option")
def config_add_option():
    """ Modify the possible options list.
        Delete, then update

        When deleting the default we need to set the database column default to NULL
    """

    option_data = json.loads(request.forms["option_data"])
    # A map of column name from moth_records table to its options table
    options_map = {
        "Location": "locations_list",
        "Trap": "traps_list",
        "Recorder": "recorders_list",
    }

    # Option
    option_name = option_data["name"]
    option_options = option_data["list"]
    option_default = option_data["default"]
    try:
        option_default = request.forms["default_option"]
    except KeyError:
        option_default = "NULL"

    # Empty table
    get_table(f"TRUNCATE {options_map[option_name]}")

    # Refill table
    for opt_details in option_options:
        quote_list = [f'"{v}"' for v in opt_details.values()]
        get_table(
            f"INSERT INTO {options_map[option_name]} VALUES ({', '.join(quote_list)});"
        )

    # Update default in moth_records
    update_moth_taxonomy.set_column_default(option_name, option_default)
    return config_options()


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
