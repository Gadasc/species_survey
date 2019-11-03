<!DOCTYPE html>

<html>
<head>
<meta http-equiv="cache-control" content="no-cache" />
<title>Merrington House Moth Survey</title>
<link rel="stylesheet" type="text/css" href="/static/autocomplete.css">
<link rel="stylesheet" type="text/css" href="/static/mothmenu.css">
<link rel="stylesheet" type="text/css" href="/static/mothgrid.css">
</head>

<body>
% include("menu_moth.tpl")
<h1>Moth Summary</h1>
<h2>Annual Species Count</h2>
<img src={{summary_image_file}} alt="Cummulative Species Summary Graph" >
<img src={{by_month_image_file}} alt="By Month Summary Graph" >
<p>
{{!moth_grid_css}}
<div class=center>
<div class=grid-parent>
<div class="grid-container moth-grid-container">
{{!moth_grid_cells}}
</div>
</div>
</div>

</body>
</html>
