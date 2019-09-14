#! /usr/local/bin/python3.7

import sqlite3
import os
from bottle import (
    route,
    run,
    debug,
    template,
    request,
    static_file,
    error,
    TEMPLATE_PATH,
)

# only needed when you run Bottle on mod_wsgi
from bottle import default_app

DATABASE_FILE = "todo.db"

os.chdir(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH.insert(0, os.getcwd())


@route("/debug")
def debug_info():
    return "TEMPLATE_PATH: " + str(TEMPLATE_PATH) + "</p>" + DATABASE_FILE


@route("/")
@route("/todo")
def todo_list():

    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute("SELECT id, task FROM todo WHERE status LIKE '1'")
    result = c.fetchall()
    c.close()

    result = [[row[0], f'<a href="/edit/{row[0]}">{row[1]}</a>'] for row in result]
    output = template("make_table", rows=result)
    return output


@route("/new", method="GET")
def new_item():

    if request.GET.save:

        new = request.GET.task.strip()
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()

        c.execute("INSERT INTO todo (task,status) VALUES (?,?)", (new, 1))
        new_id = c.lastrowid

        conn.commit()
        c.close()

        return (
            "<p>The new task was inserted into the database, the ID is %s</p>" % new_id
        )

    else:
        return template("new_task.tpl")


@route("/edit/<no:int>", method="GET")
def edit_item(no):
    print(f"Editting: {str(no)}")

    if request.GET.save:
        edit = request.GET.task.strip()
        status = request.GET.status.strip()

        if status == "open":
            status = 1
        else:
            status = 0

        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        c.execute(
            "UPDATE todo SET task = ?, status = ? WHERE id LIKE ?", (edit, status, no)
        )
        conn.commit()

        return (
            template("menu.tpl")
            + "<p>The item number %s was successfully updated</p>" % no
        )
    else:
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        c.execute("SELECT task FROM todo WHERE id LIKE ?", (str(no),))
        cur_data = c.fetchone()

        return template("edit_task", old=cur_data, no=no)


@route("/item<item:re:[0-9]+>")
def show_item(item):

    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute("SELECT task FROM todo WHERE id LIKE ?", (item,))
    result = c.fetchall()
    c.close()

    if not result:
        return "This item number does not exist!"
    else:
        return "Task: %s" % result[0]


@route("/help")
def help():

    static_file("help.html", root=".")


@route("/json<json:re:[0-9]+>")
def show_json(json):

    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute("SELECT task FROM todo WHERE id LIKE ?", (json,))
    result = c.fetchall()
    c.close()

    if not result:
        return {"task": "This item number does not exist!"}
    else:
        return {"task": result[0]}


@error(403)
def mistake403(code):
    return "There is a mistake in your url!"


@error(404)
def mistake404(code):
    return "Sorry, this page does not exist!"


if __name__ == "__main__":
    debug(True)

    # If database file doesn't exist - then create it.
    if not os.path.exists(DATABASE_FILE):
        conn = sqlite3.connect(
            DATABASE_FILE
        )  # Warning: This file is created in the current directory
        conn.execute(
            "CREATE TABLE todo (id INTEGER PRIMARY KEY, task char(100) NOT NULL, "
            "status bool NOT NULL)"
        )
        conn.commit()

    run(host="localhost", reloader=True, port=8081)
    # remember to remove reloader=True and debug(True) when you move your
    # application from development to a productive environment
