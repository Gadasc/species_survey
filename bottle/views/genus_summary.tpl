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
<h1>{{genus}}</h1>

<div style="position: relative;">
<img style="position: relative; top: 0px; left: 0px;" src="/graphs/{{genus}}" />
<img style="position: absolute; top: 0px; left: 0px;" src="/graphs/date_overlay" />
</div>

<div>
<ul>
<%
list_items = ""
for s in species:
    list_items += f"<li><a href='/species/{s}'>{s}</a></li>"
    end
%>
{{!list_items}}
</ul>
</div>


</body>
</html>
