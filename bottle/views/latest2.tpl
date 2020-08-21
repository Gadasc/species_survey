<!DOCTYPE html>

<html>
<head>
<meta http-equiv="cache-control" content="no-cache" />
<title>Merrington House Moth Survey</title>
<script src="/static/vue.js"></script>
<link rel="stylesheet" type="text/css" href="/static/mothmenu.css">
<link rel="stylesheet" type="text/css" href="/static/latest.css">
</head>

<body>
% include("menu_moth.tpl")
<h1>Latest Moth Catches</h1>
<p> </p>
<div id="app"  />



</body>

<script>

var ffy = {{ !ffy }};
var nft=  {{ !nft }};


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

Vue.component("record_row", {
    template: `
    <tr>
        <th :class="{ffy: is_ffy, nft: is_nft}"> \{\{ record_species \}\} </th>
        <td v-for="data_item in record_data" class="td_classes">\{\{ data_item \}\}</td>
    </tr>`,
    props:["record_data", "record_species"],
    data: function(){
        return {}
    }, 
    computed: {
        is_nft: function(){
            return (nft.includes(this.record_species));
        },
        is_ffy: function(){
            return (ffy.includes(this.record_species));
        },
        td_classes:function(){

        }

    }

})

vm = new Vue({
    el: '#app',
    template: `    
    <div>
    <table>
    <tr><th>Date</th>
        <th v-for="mn in months" :key="mn.name" :colspan="mn.count">\{\{ mn.name \}\}</th>
    </tr>
    <tr><th>Species</th>
    <th v-for="day in days">\{\{ day \}\}</th>
    </tr>
    <record_row v-for="species, index in all_records.index" 
        :key="species" 
        :record_data="all_records.data[index]" 
        :record_species="species"></record_row>
    </table>
    </div>`,
    data: {
        all_records: {{ !records }},
    },
    computed:{
        ccs_classes: function(){
            
        },
        days: function(){
            var days_index = this.all_records.columns.map(function(item){return item.split("-")[2];});
            return days_index;
        },
        months: function(){
            // Return an ordered list of Object(month: size)
            var months_count = Object();
            var months_order = [];
            var biggest = {name: "", count:0};

            this.all_records.columns.forEach(function(item, index){
                this_month = item.split("-")[1] + " " + item.split("-")[0];
                if (!months_order.includes(this_month)){
                    months_order.push(this_month);
                }
                if (this_month in months_count){ 
                    months_count[this_month] += 1;
                } else {
                    months_count[this_month] = 1;
                }
                if (months_count[this_month] > biggest.count){
                    biggest.name = this_month;
                    biggest.count = months_count[this_month];
                }
            })

            return months_order.map(function(item, index){
                console.log("This: ", item, " vs biggest :", biggest.name, item.localeCompare(biggest.name));
                if (item.localeCompare(biggest.name) == 0){
                    return biggest;
                }
                return {name: item.split(" ")[0], count: months_count[item]};
            });
        }
    },
})

</script>

</html>
