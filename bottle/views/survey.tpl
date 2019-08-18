<!DOCTYPE html>

<html>
<head>
<meta http-equiv="cache-control" content="no-cache" />
<title>Merrington House Moth Survey</title>
<link rel="stylesheet" type="text/css" href="/static/autocomplete.css">
</head>

<body>


<h1>Macro Moths</h1>
<p id="todays_date">
<!-- <form id="mothsForm", autocomplete="off" action="/myapp" method="post"> -->
<form id="mothsForm", autocomplete="off" action="/handle_survey" method="post">
<!-- <form id="mothsForm", autocomplete="off" action="/cgi-bin/handle_survey.cgi"> -->
<table id="demo">
<tr id="headers"><th>Species</th><th>Rcnt</th><th>Count</th></tr>
<tr id="moth_search">
<td>
  <!--Make sure the form has the autocomplete function switched off:-->
  <div class="autocomplete" >
    <input id="myInput" type="text"  placeholder="New moth" onfocusout="validate_input()">
  </div>
</td>
<td></td><td></td></tr>
</table>

<button type="submit" onclick="validate_input()">Submit</button>
</form>

<p id="debug"></p>
<p id="debug2"></p>
<p id="debug3"></p>

<script src="/static/manifest.js"></script>
<script src="/static/autocomplete.js"></script>
<script src="/static/common_names.js"></script>

<script>

// This blanks the New moth input field when it losses focus.
// Otherwise a stale name is left in this field
function validate_input() {
	console.log("validating input");
	document.getElementById("myInput").value="";
}

// Helper function to increment/decrement the count of a table row.
function update(click_species, inc) {
	var x = parseInt(document.getElementById(click_species).value) + inc;
	x = x < 0 ? 0 : x;
	console.log("Update: " + click_species + " " + x);
	document.getElementById(click_species).value = x;
}

// Add a moth record to the input table
function printMoths(moth_object, prepend) {
	// The old apple devices don't support default values so we need this code.
	if (prepend === undefined){
		prepend = false;
	}
    var mangled_moth_name = moth_object.species.replace(/ /gi, "_");

    if (js_records && mangled_moth_name in js_records) {
	moth_object.count = js_records[mangled_moth_name];
	}
    var row = document.createElement("tr");
    row.className = "tr_survey";
    var cell1 = document.createElement("td");
    var cell2 = document.createElement("td");
    var cell3 = document.createElement("td");

    var cell1_txt = document.createTextNode(moth_object.species);
    cell1.className = "species";
    cell1.appendChild(cell1_txt);

    var cell2_txt = document.createTextNode(moth_object.recent);
    cell2.className = "recent";
    cell2.appendChild(cell2_txt);

    var cell3_form = document.createElement("div");
    //cell3_form.className = "count";

    var cell3_count = document.createElement("input");
    cell3_count.setAttribute("type", "text");
    cell3_count.className = "count";
    cell3_count.value = moth_object.count;
    cell3_count.id = mangled_moth_name;
    cell3_count.setAttribute("name", cell3_count.id);

    var cell3_input_add = document.createElement("input");
    cell3_input_add.type="button";
    cell3_input_add.value = "+";
    cell3_input_add.onclick=function(){update(mangled_moth_name, 1);};
    var cell3_input_sub = document.createElement("input");
    cell3_input_sub.type="button";
    cell3_input_sub.value = "-";
    cell3_input_sub.onclick=function(){update(mangled_moth_name, -1);};

    cell3_form.appendChild(cell3_input_sub);
    cell3_form.appendChild(cell3_count);
    cell3_form.appendChild(cell3_input_add);
    cell3.appendChild(cell3_form);

    row.appendChild(cell1);
    row.appendChild(cell2);
    row.appendChild(cell3);
    if (prepend) {
        demo_search.parentNode.insertBefore(row, demo_search.nextSibling);
    }
    else {
        demo_para.appendChild(row);
    }
}

// Called when we exit the New Moth drop down box.
function add_new_moth(new_species){
	console.log("Adding: "+ new_species);
	var new_moth_object = {species: new_species, recent:0, count:0};
	printMoths(new_moth_object, true);
	document.getElementById("myInput").value="";
}

// Helper function for extracting the moth species from the object
// This is required as older apple products don't support => operator
function get_name(moth_obj){
	var moth = moth_obj.species;
	return moth;
}

// These helper functions appear to be required because old iPads/iPhones don't seem to cope
// with the newer => operator for mapping/filtering 
function unmangle_name(mangled_name){
	return mangled_name.replace(/_/gi, " ");
}

// Helper function used in filtering out list for display
// This is required as apple devices don't support => operator
function new_moth_test(moth_name){
	return !moths_list.includes(moth_name);
}

// Using dict/json passed from bottle appliaction
var js_records = {{!records}}

// Populate the initial table
var demo_para = document.getElementById('demo');
var demo_hdrs = document.getElementById('headers')
var demo_search = document.getElementById('moth_search');
recent_moths.reverse().forEach(printMoths);

//Now add any remaining moths from the json file for today's haul
var moths_list = recent_moths.map(get_name);
console.log(moths_list);

console.log("Moths list:" + moths_list.join());
if (js_records) {
	var saved_list = Object.keys(js_records).map(unmangle_name);
	console.log("Saved list:" + saved_list);
	var difference = saved_list.filter(new_moth_test);
	console.log("New moths:" + difference);
	for (i = 0; i < difference.length; i++) {
		console.log(difference[i] + " " + js_records[difference[i]]);
		var add_moth = {species: difference[i], recent:0, count:js_records[difference[i]]};
		printMoths(add_moth, true);
	}
}

autocomplete(document.getElementById("myInput"), common_names, add_new_moth);

</script>

</body>
</html> 
