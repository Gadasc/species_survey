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
<h1>Test Vue Survey</h1>
<div id="app"  />
</body>

<script>
    Vue.component('table-row', {
        template: `
            <tr><td>\{\{record.species\}\}</td></tr>
            `,
        props:['record']
    })

    Vue.component('moth-entry', {
        template: `<tr>
                   <td>\{\{moth_record.species\}\}</td>
                   <td class="recent">\{\{moth_record.recent\}\}</td>
                   <td><button class="round_button" v-on:click='decrement'>-</button></td>
                   <td class="count">\{\{moth_record.count\}\}</td>
                   <td><button class="round_button" v-on:click="increment">+</button></td>
                   </tr>
                   `,
        props: ['moth_record'],
        methods: {
            decrement: function(){
                console.log("Decrement", this.moth_record.species)
                if (this.moth_record.count > 0){
                    this.moth_record.count -= 1;
                }
            },
            increment: function(){
                console.log("Increment", this.moth_record.species)
                this.moth_record.count += 1
            }
        }
    })

    Vue.component('match-item', {
            template: `<div v-on:click="local_clicked_me">\{\{match_species\}\}</div>`,
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
                placeholder="New moth" 
                v-on:input="list_candidates()" 
                v-on:keyup.down="process_down_event" 
                v-on:keyup.up="process_up_event"
                v-on:keyup.enter="select_species(matched_names[highlighted_species])"
                v-on:keyup.esc="select_species('')"
                v-model=search_text />
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
                return this.search_text.toLowerCase();
            }
        },
        methods: {
            match_filter: function(mname) {
                return mname.toLowerCase().includes(this.lower_search_text) && !this.current_moths.includes(mname.toLowerCase());
            },
            list_candidates: function(){
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
        <p>Date: {{!dash_date_str}}</p>
        <table>
        <thead><tr><th>Species</th><th>Recent</th><th></th><th>Count</th><th></th></tr></thead>
        <tbody>
            <tr><td colspan="5" style="width: 100%;"><auto-list-box v-on:add-species="add_species" v-bind:current_moths="current_moths"></auto-list-box></td>
            </tr>
            <moth-entry v-for="moth in moths" v-bind:key='moth.species' v-bind:moth_record='moth' />
        </tbody>
        </table>
        </div>
        `,
       
        data: function() {
            return {
                manifest_moths: [], 
                captured_moths: [],
                //moths: []
            }
        },
        //props: ["moths"],
        methods: {
            add_species: function(new_species){
                console.log(new_species);
                this.moths.unshift({"species": new_species, "recent": 0, "count": 0});
            }
        },
        computed: {
            // create a lower case list of moth names that are already in the survey sheet.
            // The match list can use this to avoid duplicates
            current_moths: function(){
                return this.moths.map(function(item){return item.species.toLowerCase();});
            },
            moths: function() {
                // combine manifest_moths and captured moths
                var all_moths = []
                this.manifest_moths.forEach(function(item, index){all_moths.push(item)});
                this.captured_moths.forEach(function(item, index){all_moths.push(item)});
                return all_moths;      
            }   
            //this.captured_moths.foreach(function(elem, index){console.log(elem.species);});
        }
        
        
    })
    vm.manifest_moths = recent_moths;
    vm.captured_moths = {{!records}};
    //vm.moths = recent_moths;
</script>

<style>
    
</style>

</html>