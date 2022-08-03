<!DOCTYPE html>

<html>
<head>
<meta http-equiv="cache-control" content="no-cache" />
<title>Moth Survey</title>
<link rel="stylesheet" type="text/css" href="/static/mothmenu.css">
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
</head>

<body>
% include("menu_moth.tpl")
<h1>{{family}}</h1>

<div style="position: relative;" id="familyGraph"></div>

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

<script>
    Plotly.newPlot('familyGraph', {{!fg}});
</script>
</html>
