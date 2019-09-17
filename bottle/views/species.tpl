<!DOCTYPE html>

<html>
<head>
<meta http-equiv="cache-control" content="no-cache" />
<title>Merrington House Moth Survey</title>
<link rel="stylesheet" type="text/css" href="/static/autocomplete.css">
<link rel="stylesheet" type="text/css" href="/static/mothmenu.css">
</head>

<body>
% include("menu_moth.tpl")
<h1>{{species}}</h1>

<div style="position: relative;">
<img style="position: relative; top: 0px; left: 0px;" src="/graphs/{{species}}" />
<img style="position: absolute; top: 0px; left: 0px;" src="/graphs/date_overlay" />
</div>

<div>
{{!catches}}
</div>


</body>
</html>
