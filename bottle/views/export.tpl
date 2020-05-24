<head>
<meta http-equiv="cache-control" content="no-cache" />
<title>Merrington House Moth Survey</title>
<link rel="stylesheet" type="text/css" href="/static/mothmenu.css">
<script src="/static/vue.js"></script>

</head>

<body>
% include("menu_moth.tpl")
<h1>Download Records</h1>

<div id="app">
</div>
</body>

<style>
.inFuture  {
    color: lightgrey;
}
.preHistory {
    opacity: 0;
}

.yeardl {
    background: #38495f;
    color: white ;
    padding: 10px;
    border: 10px;
    margin: 10px;
}

.monthdl {
    background: #b7c8de;
    padding: 10px;
    margin: 1px;

}

.monthdl > a {
    text-decoration: none;
    color: inherit;
}

.dlcontainer {
    margin: 30px;
    font-size: 24px;

}

.dlcontainer > a {
    text-decoration: none;
}


</style>

<script>
Vue.component('monthDownloader', {
    template: `
        <span class="monthdl" v-bind:class=classObject>
            <a v-bind:href="url" :download="download_fname">\{\{toMonthName(myMonth)\}\}</a>
        </span>
        `,
    props: ['myYear', 'myMonth'],
    methods: {
        toMonthName: function(monthNumber) {
            const tempDate = new Date(2020, monthNumber, 1);
            return tempDate.toLocaleString('default', {month: 'short'});
        },
    },
    computed: { 
        classObject: function() {
            d = new Date();
            thisYear = d.getFullYear()
            thisMonth = d.getMonth()
            return {
                
                inFuture: this.myYear == thisYear && this.myMonth > thisMonth,
                preHistory: this.myYear <= {{e_year}} && this.myMonth < {{e_month}}  
            }
        },
        url: function() {
                /* Where Jan = 1 and Dec = 12
                */
                return "/download/" + this.myYear + "/" + (this.myMonth+1);
        },
        download_fname: function() {
            return "moth_records_" + this.myYear + "_" + (this.myMonth+1) +".csv";
        }
     
    }
})


Vue.component('yearDownloader', {
    template: `
        <div class="dlcontainer">
            <a v-bind:href="url" class="yeardl" :download="download_fname">\{\{myYear\}\}</a>
            <monthDownloader v-for="mn in 12" :myMonth="mn-1" :myYear="myYear" />
        </div>
        `,
    props: ['myYear'],
    computed: {
        url: function() {
                /* Where Jan = 1 and Dec = 12
                */
                return "/download/" + this.myYear;
        },
        download_fname: function() {
            return "moth_records_" + this.myYear + ".csv";
        }
    }
})


vm = new Vue({
    el: "#app",
    template: `
        <div>
        <yearDownloader v-for="yyyy in yyyy_range" v-bind:myYear="thisYear - yyyy + 1" />
        </div>`,
    computed: {
        yyyy_range: function() {
            return this.thisYear - {{e_year}} + 1;
        },
        thisYear: function() {
            d = new Date();
            return d.getFullYear();
        }
        
    },
    
        
    
})

</script>


</html>
