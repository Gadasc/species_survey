# species_survey

## Disclaimer - This was built initially for my personal use specifically for recording moths. Anyone using this is likely to find some rough edges and gotchas. Please let me know and I'll endevour to fix - better yet send me a pull request.

## Which branch?
I recommend taking the latest from the __deploy__ branch.

## Installation
Very little effort has been spent on making the install process smooth.
Having said that I do believe there are only a few steps needed:

1. clone the repo to your local machine
2. Install/config a mysql or mariadb server - I use mariadb, so that is recommended. (See notes below about installation). If you would rather use a sqlite3 filebased (and get the app to set this up for you, let me know)
3. create a file sql_config_local.py to override the values in sql_config.py
4. Ensure you have installed the dependancies 
```pip install markdown numpy bottle pandas mysql.connector waitress```
5. Install Vue.js version 2 into the ./bottle/static directory: `wget https://raw.githubusercontent.com/vuejs/vue/2.6/dist/vue.js` 
5. run moth_bottle.py (I run this from a crontab at boot)
6. point a brower at <your machine>:8082

HOLD FIRE: I'm working through a fresh install with the latest external dependancies. I've found one bug that was benign with my old version of pandas but throws and exception witht he latest. 
Good luck and let me know how it goes.
  
  
  
## Installing and configuring mariadb
There is a good tutorial here: https://raspberrytips.com/install-mariadb-raspberry-pi/
  
Follow this tutorial to set up root access from the local machine

The specific instructions needed to define the user details in sql_config_default.py are:

  1. Login as root: `sudo mysql -uroot -p`
  2. Create database: `CREATE DATABASE moths_database;`
  3. Create user: `CREATE USER `'moths'@'localhost' IDENTIFIED BY 'moths12345';`
  4. Grant privileges: `GRANT ALL PRIVILEGES ON moths_database.* TO 'moths'@'localhost';`
  5. Finally: `FLUSH PRIVILEGES;`
  
If you want to change the database name, username or password - just make sure you create a sql_config_local.py that overrides the default values to set them to the values you use here.
  
## Populating the database
Remember that disclaimer? Well here's the first hack.

  1. Rename/copy the file 20200810_irecord_names.csv to 20200429_moth_names_all.csv.
  `cp 20200810_irecord_names.csv 20200429_moth_names_all.csv `
  2. run the script  `python create_tables.py`
  3. _HACK 2_ login again to mysql: `sudo mysql -uroot -p`
  4. Add the column TVK: `ALTER TABLE moth_taxonomy ADD COLUMN TVK varchar(50);`
  5. Rename the table: `RENAME TABLE moth_taxonomy TO irecord_taxonomy;`
  
