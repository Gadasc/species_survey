<!DOCTYPE html>
<html>
<head>
    <script src="/static/vue.js"></script>
    <script src="/static/common_names.js"></script>
    <link rel="stylesheet" type="text/css" href="/static/vue_survey.css">
    <link rel="stylesheet" type="text/css" href="/static/mothmenu.css">
</head>
<body>
    % include("menu_moth.tpl")
<h1>Moth Survey - Home</h1>
<div id="app"  />
</body>

<script>
    Vue.component('table-row', {
        template: `
            <tr><td>\{\{record.species\}\}</td></tr>
            `,
        props:['record']
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
            <div style="width: 50%;" class="match_list_container">
            <input type="text"
                autocomplete="off" 
                placeholder="Search moth names" 
                v-on:input="list_candidates()" 
                v-on:keyup.down="process_down_event" 
                v-on:keyup.up="process_up_event"
                v-on:keyup.enter="select_species(matched_names[highlighted_species])"
                v-on:keyup.esc.prevent="clear_search"
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
                first_match = this.matched_names.length ? this.matched_names[0] : null 
                this.matched_names = [];
                this.highlighted_species = null;
                console.log("Selected species: " + this.selected_species);
                // Only add the species if it is valid
                if(value !== "" && typeof value !== 'undefined') {
                    console.log("Return: " + this.selected_species + " as match for: " + this.search_text);
                    this.$emit("add-species", this.selected_species);
                } else if(typeof first_match !== 'undefined'){
                    console.log("Return 1st entry: "+ first_match);
                    this.$emit("add-species", first_match);
                }
            },
            clear_search: function() {
                this.search_text = "";
                this.matched_names = [];
                this.highlighted_species = null;
            },
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
        <auto-list-box v-on:add-species="select_species" v-bind:current_moths="current_moths"></auto-list-box>
        </div>
        `,
       
        data: function() {
            return {
                moths: [],
                current_moths: []
            }
        },
        //props: ["moths"],
        methods: {
            select_species: function(new_species){
                // link to ./species/new_species
                window.location.href = "./species/"+ new_species;
            }
        }
        
        
        
    })


</script>

<style>
    
</style>

</html>