<!DOCTYPE html>

<html>
<head>
<title>Merrington House Moth Survey</title>
<meta http-equiv="cache-control" content="no-cache" />
<script src="/static/vue.js"></script>
<link rel="stylesheet" type="text/css" href="/static/mothmenu.css">
<link rel="stylesheet" type="text/css" href="/static/latest.css">
</head>

<body>
% include("menu_moth.tpl")
<h1>Options</h1>
<p> </p>
<div id="app"></div>
<hr>

</body>

<script>

Vue.component("options", {
    template: `<div>
        <h2>\{\{ option_data["name"] \}\} List</h2>
        </p>
        <form action="/add_option" method="post">
        <table>
            <input type="hidden" name="option_data" :value="json_option_data">
            <tr><th v-for="col in option_data.option_template">\{\{ col \}\}</th><th>Default</th></tr>
            <tr v-for="oi in option_data.list" >
                <td v-for="ci in oi">\{\{ ci \}\}</td>
                <td><input type="radio" name="default_item" :value="Object.values(oi)[0]" v-model="default_item" v-on:change="radio_change"></td>
                <td><input type="button" name="delete_item" value="X" @click="delete_option_item($event, option_data['name'], Object.values(oi)[0])"></td>
            </tr>
            <tr>
                <td v-for="col in option_data.option_template">
                <input type="text" id="col"  :placeholder="col" v-model:value="new_item[col]">
                </td>
                <td><input type="radio" name="default_item" value="new_item" v-model="default_item" v-on:change="radio_change"></td>
                <td><input type="button" name="add_item" :disabled="isNewDisabled" value="+" @click="add_option_item($event, option_data['name'], new_item)"></td>
            </tr>
        </table>
        <input type="submit">
        </form>
        <hr>
        </div>`,
    props: ['option_data'],
    data: function(){
        return {
            default_item: this.option_data.default,
            new_item: {}
        }
    },
    watch: {
            default_item: {
                handler(val) {
                    this.update_default_value(this.option_data.name, val);
                },
                deep: true
            }
        },
    computed: {
        isNewDisabled: function(){
            console.log("Values: ", (Object.values(this.new_item)));
            console.log("Length of new item:", Object.keys(this.new_item).length);
            console.log("Length of item:", this.option_data.option_template.length);

            if (Object.keys(this.new_item).length != this.option_data.option_template.length){
                return true;
            }
            if (Object.values(this.new_item).includes("")){
                return true;
            }
            /* Prevent duplicate entries */
            console.log("List values", this.existingValues);
            if (this.existingValues.includes(Object.values(this.new_item)[0])){
                return true;
            }

            return false;
        },
        existingValues: function(){
            return this.option_data.list.map(function(obj){return Object.values(obj)[0]});
        },
        json_option_data: function(){
            return JSON.stringify(this.option_data);
        }
    },
    methods: {
        delete_option_item: function(event, o_type, o_val){
            console.log("Delete Event", o_type, o_val);
            console.log("Default: ", this.default_item);
            if(o_val == this.default_item){
                this.default_item = null;
            }
            this.$emit("delete_option_item", o_type, o_val);
        },
        add_option_item: function(event, o_type, item_val){
            console.log("Add Event", o_type, item_val);
            this.$emit("add_option_item", o_type, item_val);
            console.log("Def: ", this.default_item);
            if (this.default_item == "new_item"){
                console.log("Setting def to: ", Object.values(item_val)[0]);
                this.default_item = Object.values(item_val)[0];
            }
            this.new_item = {};
        },
        radio_change: function(event){
            console.log("Radio change", event.target.value);
        },
        update_default_value: function(option_name, val){
            console.log("Updateing default ", option_name, val);
            this.$emit("update_option_default", option_name, val);
        }

    }

})

vm = new Vue({
    el: '#app',
    template: `    
    <div>
        <options v-for="opt in detail_options" 
            :option_data="opt" 
            :key="opt.name"
            v-on:delete_option_item="delete_option_item"
            v-on:add_option_item="add_option_item"
            v-on:update_option_default="update_option_default"
        >
        </options>
    </div>
    `,
    
    data: {
            detail_options: {
                "Location": {name: "Location", list: {{!location_list}}, default: "{{!default_location}}", column_hdr: "Loc", hidden: true, option_template: {{!location_template }} },
                "Recorder": {name: "Recorder", list: {{!recorder_list}}, default: "{{!default_recorder}}", column_hdr: "Rec", hidden: true, option_template: {{!recorder_template }} },
                "Trap": {name: "Trap", list: {{!trap_list}}, default: "{{!default_trap}}", column_hdr: "Trap", hidden: true, option_template: {{!trap_template }} }
            }
    },
    methods: {
        delete_option_item: function(o_type, o_val){
            values = this.detail_options[o_type].list;
            first_field = this.detail_options[o_type].option_template[0];
            i = values.findIndex(function(obj, ind){return obj[first_field] == o_val});
            if (i > -1){
                values.splice(i, 1)
            }
            console.log(values);
        },
        add_option_item: function(o_type, item_val){
            console.log("Add new item", o_type, item_val);
            this.detail_options[o_type].list.push(item_val);
        },
        update_option_default: function(o_type, o_val){
            this.detail_options[o_type].default = o_val;
        }

    }
})
</script>
</html>