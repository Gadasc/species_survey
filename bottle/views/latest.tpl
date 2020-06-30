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
<h1>Latest Moth Catches</h1>
<p> </p>
{{!html_table}}

</body>

<script>
    // This code will look for a cookie "delete_cache_date" and delete the sessionStorage 
    // data with that key. Finally the cookie is removed.
    var cindex = document.cookie.indexOf("delete_cache_date="); 
    console.log("cindex=", cindex);
    if (cindex != -1){
        dash_date_string = document.cookie.substr(cindex+"delete_cache_date=".length, "YYYY-MM-DD".length);
        console.log("dash_date_string=", dash_date_string);
        sessionStorage.removeItem(dash_date_string);
        document.cookie = "delete_cache_date=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
    }
</script>

</html>
