<!DOCTYPE html>

<html>
<head>
<meta http-equiv="cache-control" content="no-cache" />
<title>Merrington House Moth Survey</title>
<link rel="stylesheet" type="text/css" href="/static/mothmenu.css">
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
</head>

<body>
% include("menu_moth.tpl")
<h1>{{species}}</h1>
<div>{{!taxonomy}}</div>

<div id="mothGraph">

</div>


<div style="width: 800px;">
{{!catches}}
</div>


</body>

<script>
    Plotly.newPlot('mothGraph', {{!plotly_data}});
</script>


</html>
