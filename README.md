# species_survey

## Disclaimer - This was built initially for my personal use specifically for recording moths. Anyone using this is likely to find some rough edges and gotchas. Please let me know and I'll endevour to fix - better yet send me a pull request.

## Which branch?
I recommend taking the latest from the __deploy__ branch.

## Installation
Very little effort has been spent on making the install process smooth.
Having said that I do believe there are only a few steps needed:

1. clone the repo to your local machine
2. Install/config a mysql or mariadb server - I use mariadb, so that is recommended. If you would rather use a sqlite3 filebased (and get the app to set this up for you, let me know)
3. create a file sql_config_local.py to override the values in sql_config.py
4. Ensure you have installed the dependancies 
```pip install markdown numpy bottle pandas mysql.connector```
5. run moth_bottle.py (I run this from a crontab at boot)
6. point a brower at <your machine>:8082

Good luck and let me know how it goes.
