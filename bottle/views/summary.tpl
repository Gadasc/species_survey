<!DOCTYPE html>

<html>
<head>
<meta http-equiv="cache-control" content="no-cache" />
<title>Merrington House Moth Survey</title>
<link rel="stylesheet" type="text/css" href="/static/mothmenu.css">
<link rel="stylesheet" type="text/css" href="/static/mothgrid.css">
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
</head>

<body>
% include("menu_moth.tpl")
<h1>Moth Summary</h1>
<h2>Annual Species Count</h2>
<div id="cummulativeGraph"></div>
<div id="byMonthGraph"></div>
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

<script>
    Plotly.newPlot('cummulativeGraph', {{!summary_graph_json}});
    Plotly.newPlot('byMonthGraph', {{!by_month_graph_json}});
</script>
</html>
