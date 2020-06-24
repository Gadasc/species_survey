<!DOCTYPE html>
<html>
<head>
    <script src="/static/vue.js"></script>
    <script src="/static/manifest.js"></script>
    <script src="/static/common_names.js"></script>
    <link rel="stylesheet" type="text/css" href="/static/vue_survey.css">
    <link rel="stylesheet" type="text/css" href="/static/mothmenu.css">
</head>
<body>
    % include("menu_moth.tpl")
<h1>Moth Survey Sheet</h1>
<div id="app"  />
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

<script>

    // Helper functions to store updates in sessionStorage until successfully commited.
    // This protects against accidentally leaving the page, or network failures.
    function cache_update_species(species_obj){
        record_cache[species_obj.species] = species_obj;
        sessionStorage.setItem("{{!dash_date_str}}", JSON.stringify(record_cache));
    }

 
    Vue.component('table-row', {
        template: `
            <tr><td>\{\{record.species\}\}</td></tr>
            `,
        props:['record']
    })

    Vue.component('moth-entry', {
        template: `<tr>
                   <td v-bind:class="{'virgin' : isVirgin, 'updated': isUpdated}">\{\{moth_record.species\}\}</td>
                   <td class="recent">\{\{moth_record.recent\}\}</td>
                   <td><button class="round_button" v-on:click.prevent='decrement'>-</button></td>
                   <td class="count" v-bind:class="{'virgin' : isVirgin, 'updated': isUpdated}"><input v-bind:name="moth_record.species" v-model="moth_record.count"></td>
                   <td><button class="round_button" v-on:click.prevent="increment">+</button></td>
                   </tr>
                   `,
        props: ['moth_record'],
        methods: {
            decrement: function(){
                console.log("Decrement", this.moth_record.species)
                if (this.moth_record.count > 0){
                    this.moth_record.count -= 1;
                    this.moth_record.virgin = false;
                    this.moth_record.updated = true;
                    cache_update_species(this.moth_record);
                }
            },
            increment: function(){
                console.log("Increment", this.moth_record.species);
                this.moth_record.count += 1;
                this.moth_record.virgin = false;
                this.moth_record.updated = true;
                cache_update_species(this.moth_record);
            }
        },
        computed: {
            isVirgin: function(){
                return this.moth_record.virgin;
            },
            isUpdated: function(){
                return this.moth_record.updated;
            }
        }
    })

    Vue.component('match-item', {
            template: `<div v-on:click.prevent="local_clicked_me">\{\{match_species\}\}</div>`,
            props: ['match_species'],
            methods: {
                // Functions go here
                local_clicked_me: function(){
                    console.log("Local clicked me"+this.match_species);
                    this.$emit("clicked_me", this.match_species);
                }
            }

    })


    Vue.component('auto-list-box', {
        template: `
            <div class="match_list_container">
            <input type="text"
                autocomplete="off" 
                placeholder="New moth" 
                v-on:input="list_candidates" 
                v-on:keyup.down="process_down_event" 
                v-on:keyup.up="process_up_event"
                v-on:keyup.enter="select_species(matched_names[highlighted_species])"
                v-on:keyup.esc="select_species('')"
                v-model="search_text"    
                />
            <div class="match_list_item">
            <match-item  
                v-for="match in matched_names" 
                v-bind:match_species=match 
                v-bind:key=match 
                v-on:clicked_me="select_species" 
                v-bind:class='{"match_list_item-active": (match === matched_names[highlighted_species])}' />
            </div>
            </div>
            `,
        data: function() {
            return {moth_names: common_names,
                    search_text: "",
                    matched_names: [],
                    selected_species: "",
                    highlighted_species: null}
        },
        props: ['current_moths'],
        computed: {
            lower_search_text: function(){
                return this.search_text.toLowerCase().replace(/[^a-z]/g, " ");
            }
        },
        methods: {
            match_filter: function(mname) {
                return mname.toLowerCase().replace(/[^a-z]/g, " ").includes(this.lower_search_text) && !this.current_moths.includes(mname.toLowerCase());
            },
            list_candidates: function(event){
                this.search_text = event.target.value;
                console.log("Search changed: " + this.search_text);
                this.highlighted_species = null;
                if (this.search_text.length > 2) {
                    this.matched_names = this.moth_names.filter(this.match_filter);
                } else {
                    this.matched_names = [];
                }
                console.log(this.matched_names);
            },
            select_species: function(value) {
                this.selected_species = value;
                this.search_text = "";
                this. matched_names = [];
                this.highlighted_species = null;
                console.log("Selected species: " + this.selected_species);
                // Only add the species if it is valid
                if(value !== "" && typeof value !== 'undefined') {
                    this.$emit("add-species", this.selected_species)

                }

            } ,
            process_down_event: function(event){
                console.log("auto-list-box DOWN: " + event.type );
                if (this.highlighted_species != null){
                    this.highlighted_species += 1;
                    this.highlighted_species %= this.matched_names.length;
                }else{
                    this.highlighted_species = 0;
                }
            },
            process_up_event: function(event){
                console.log("auto-list-box UP: " + event.type );
                if (this.highlighted_species != null){
                    this.highlighted_species -= 1;
                    this.highlighted_species += this.matched_names.length;
                    this.highlighted_species %= this.matched_names.length;
                }else{
                    this.highlighted_species = this.matched_names.length-1;
                }
            }
        }
    })

    vm = new Vue({
        el: '#app',
        template: `    
        <div>
        <form id="mothsForm" autocomplete="off" action="/handle_survey" method="post" v-on:keydown.enter.prevent>
        Date: <a class=daynav v-bind:href=yesterday>&#9664;</a>
              <input class="survey_date" type="text" name="dash_date_str"  value="{{!dash_date_str}}" readonly>
              <a class=daynav v-bind:href=tomorrow>&#9654;</a></p>
        <table>
        <thead><tr><th>Species</th><th>Recent</th><th></th><th>Count</th><th></th></tr></thead>
        <tbody>
            <tr><td colspan="5" style="width: 100%;"><auto-list-box v-on:add-species="add_species" v-bind:current_moths="current_moths"></auto-list-box></td>
            </tr>
            <moth-entry v-for="moth in moths" v-bind:key='moth.species' v-bind:moth_record='moth' />
        </tbody>
        </table>
        <button type="submit">Submit</button>
        </form>
        </div>
        `,
       
        data: function() {
            return {
                moths: []
            }
        },
        methods: {
            add_species: function(new_species){
                console.log(new_species);
                var species_object = {"species": new_species, "recent": 0, "count": 0, "virgin": true, "updated": false,};
                this.moths.unshift(species_object);

                // Add species to sessionStorage
                cache_update_species(species_object);
            },
            formatDate: function(date) {
                var d = new Date(date),
                    month = '' + (d.getMonth() + 1),
                    day = '' + d.getDate(),
                    year = d.getFullYear();

                if (month.length < 2) 
                    month = '0' + month;
                if (day.length < 2) 
                    day = '0' + day;

                return [year, month, day].join('-');
            }
        },
        computed: {
            // create a lower case list of moth names that are already in the survey sheet.
            // The match list can use this to avoid duplicates
            current_moths: function(){
                return this.moths.map(function(item){return item.species.toLowerCase();});
            },
            yesterday: function(){
                tdy = new Date("{{!dash_date_str}}");
                tdy.setHours(12);
                ms = tdy.getTime();
                ms-= 24*60*60*1000;
                return "/survey/"+this.formatDate(ms);
            },
            tomorrow: function(){
                tdy = new Date("{{!dash_date_str}}");
                tdy.setHours(12)
                ms = tdy.getTime();
                ms += 24*60*60*1000;
                return "/survey/"+this.formatDate(ms);
            }
        }
        
        
    })

    // On load we want to combine the likely moths from the manifest and the recently seen moths.
    // This combination is not reactive so can be done once on load. 

    manifest_moths = recent_moths;  // From manifest.js
    captured_moths = {{!records}};
    // combine manifest_moths and captured moths
    var all_moths = []
    // First add recently seen species from the manifest
    manifest_moths.forEach(function(item, index){
            item.virgin = false;
            item.updated = false;
            all_moths.push(item);
        }
    );
    
    // Now add anything already recorded for this date, add if not a recent species, and update
    // record if it already exists.
    captured_moths.forEach(function(item, index){
        // If exists - find index and update record
        first_match = all_moths.findIndex(function(v){return (v.species == item.species)});
        if (first_match !== -1) {
            // Find index
            console.log("Found duplicate record for " + item.species + " at: " + first_match);
            // Update record only if the record is null
            all_moths[first_match].count = item.count;
        // else add to list
        } else {
            all_moths.push(item);
        }
    });

    // Now ensure the list is sorted
    all_moths.sort(function(i1, i2){return i1.species.localeCompare(i2.species)});

    // Now we can check for anything stored in the browser cache.
    var record_cache = JSON.parse(sessionStorage.getItem("{{!dash_date_str}}"));
    if (record_cache == null){
        record_cache = {};
    } else {
        console.log("Retrieved sessionStorage", record_cache);
        Object.entries(record_cache).forEach(function(kv, index){
            var mname = kv[0];
            var mobj = kv[1];
            console.log(mobj);

            // If exists - find index and update record
            first_match = all_moths.findIndex(function(v){return (v.species == mname)});
            if (first_match !== -1) {
                // Find index
                console.log("Found existing record for " + mname + " at: " + first_match);
                // Update record only if the record is null
                all_moths[first_match] = mobj;
            // else add to list
            } else {
                all_moths.unshift(mobj);
            }
        });
    }
    
    // Finally inject into the app
    vm.moths = all_moths;      

</script>

</html>

