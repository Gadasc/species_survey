<!DOCTYPE html>

<html>
<head>
<meta http-equiv="cache-control" content="no-cache" />
<title>Merrington House Moth Survey</title>
<link rel="stylesheet" type="text/css" href="/static/mothmenu.css">
<link rel="stylesheet" type="text/css" href="/static/latest.css">
</head>

<body>
% include("menu_moth.tpl")
<h1>Options</h1>
<p> </p>
<hr>
<h2>Location List</h2>
Default Location = {{def_location}}</p>
Locations = {{location_list}}</p>
<form action="/add_location" method="post">
    <input id="new_loc_name" name="new_loc_name" type="text" placeholder="New location name">
    <input id="new_loc_pos" name="new_loc_pos" type="text" placeholder="Grid Ref">
    Default<input id="new_loc_def" name="new_loc_def" type="checkbox" value=True> 
    Delete<input id="delete_loc" name="delete_loc" type="checkbox" value=True> 
    <input type="submit">
</form>
</p>
<hr>
<h2>Recorder List</h2>
Default Recorder = {{def_recorder}}</p>
Recorders = {{recorder_list}}</p>
<form action="/add_recorder" method="post">
    <input id="new_recorder_name" name="new_recorder_name" type="text" placeholder="New recorder name">
    Default<input id="new_recorder_def" name="new_recorder_def" type="checkbox" value=True>
    Delete<input id="delete_recorder" name="delete_recorder" type="checkbox" value=True> 
    <input type="submit">
</form>
<hr>
</p>
<h2>Trap List</h2>
Default trap = {{def_trap}}</p>
Lamps = {{trap_list}}</p>
<form action="/add_trap" method="post">
    <input id="new_trap_name" name="new_trap_name" type="text" placeholder="New trap name">
    Default<input id="new_trap_def" name="new_trap_def" type="checkbox" value=True> 
    Delete<input id="delete_trap" name="delete_trap" type="checkbox" value=True> 
    <input type="submit">
</form>

<hr>



</body>
</html>