// TODO: change marker type

var m_top = 4000,
    m_left = 4000,
    center_lat = 40.71,
    center_lon = -73.98,
    se_bound = new google.maps.LatLng(40.49, -74.31),
    nw_bound = new google.maps.LatLng(40.84, -73.75);

var mapOptions = {
    draggableCursor: 'crosshair',

    zoom: 11,
    center: new google.maps.LatLng(center_lat, center_lon),
    //mapTypeId: google.maps.MapTypeId.TERRAIN,
    mapTypeId: google.maps.MapTypeId.ROADMAP,
    minZoom: 10,  //NYC centric


    //panControl: false,
    //zoomControl: false,
    mapTypeControl: false,
    scaleControl: false,
    streetViewControl: false,
    overviewMapControl: false,
    rotateControl: false,
    disableDoubleClickZoom: true,
    //scrollwheel: false,
    //draggable: false,
    keyboardShortcuts: false
};

var all_grid_data = d3.map();

//Spinner
var spinner = new Spinner();
var spin_target = document.getElementById('loading');
spinner.spin(spin_target);



// Queue up the data files
queue()
    .defer(d3.json, "/static/nyc_border.geojson")
    .defer(d3.json, "/static/grid.geojson")
    .defer(d3.csv, "/static/grid_locs.csv")
    .defer(d3.csv, "/static/breakpoints.csv")
    .defer(d3.csv, "/grid_data.csv")
    .await(ready);

var marker;

function ready(error, nyc_border_data, grid_json, grid_locs, breakpoints, grid_dat){

    if (error) return console.error(error);

    for(ndx=0; ndx < grid_dat.length; ndx++){
        ggg = grid_dat[ndx];
        g_dat = all_grid_data.get(ggg.gr_id);

        if(typeof(g_dat) == "undefined"){
            all_grid_data.set(ggg.gr_id, [ggg]);
        }else{
            all_grid_data.set(ggg.gr_id, g_dat.concat([ggg]));
        }
    }

    var selected_metric = 'AQI';
    var geocoder = new google.maps.Geocoder();

    document.getElementById('loading').style.display = 'block';

    function getColor(d, metric){

        var domain = [];
        var range = [];

        for(x = 0; x < breakpoints.length; x++){
            if(metric == "PM25"){
                domain.push(parseFloat(breakpoints[x].PM25_24hr));
            }else if(metric == "O3"){
                domain.push(parseFloat(breakpoints[x].O3_8hr));
            }else if(metric == "AQI"){
                domain.push(parseFloat(breakpoints[x].Index));
            }
            range.push(breakpoints[x]['Color']);
        }

        var color = d3.scale.threshold().domain(domain).range(range);

        return color(d);
    }

    function getAlpha(d, metric){

        var val, lower = -1, upper;

        for(x = 0; x < (breakpoints.length - 1); x++){
            if(metric == "PM25"){
                val = parseFloat(breakpoints[x].PM25_24hr);
            }else if(metric == "O3"){
                val = parseFloat(breakpoints[x].O3_8hr);
            }else if(metric == "AQI"){
                val = parseFloat(breakpoints[x].Index);
            }

            if(d >= val){
                lower = val;
                if(metric == "PM25"){
                    upper = parseFloat(breakpoints[x+1].PM25_24hr);
                }else if(metric == "O3"){
                    upper = parseFloat(breakpoints[x+1].O3_8hr);
                }else if(metric == "AQI"){
                    upper = parseFloat(breakpoints[x+1].Index);
                }
            }
        }
        // Out of scale
        if(lower == -1){
            return 0.8;
        }

        var alpha = d3.scale.linear()
                    .domain([lower, upper])
                    .range([0.3, 0.9]);

        return alpha(d);
    }


    var nyc_border = nyc_border_data.features;

    // Load the google map
    function initialize() {

        document.getElementById('loading').style.display = 'block';

        map = new google.maps.Map(document.getElementById('d3map'),
            mapOptions);


        // Create bounds to the map
        var allowedBounds = new google.maps.LatLngBounds(
            se_bound, nw_bound
        );
        var lastValidCenter = map.getCenter();

        google.maps.event.addListener(map, 'center_changed', function() {
            if (allowedBounds.contains(map.getCenter())) {
                // still within valid bounds, so save the last valid position
                lastValidCenter = map.getCenter();
            } else {
                // not valid anymore => return to last valid position
                map.panTo(lastValidCenter);
            }
        });


        var overlay = new google.maps.OverlayView();

        overlay.onAdd = function () {

            var layer = d3.select(this.getPanes().overlayMouseTarget).append("div")
                .attr("class", "SvgOverlay");
            var svg = layer.append("svg");

            var grid = grid_json.features;

            var clip = svg.append("defs")
                        .append("clipPath")
                        .attr("id", "clippingPath")

            var grid_group = svg.append('g')
                        .attr('id', 'grid')
                        .attr("clip-path", "url(#clippingPath)") // add clipping;

            overlay.draw = function () {
                var markerOverlay = this;
                var overlayProjection = markerOverlay.getProjection();

                // Turn the overlay projection into a d3 projection
                var googleMapProjection = function (coordinates) {
                    var googleCoordinates = new google.maps.LatLng(coordinates[1], coordinates[0]);
                    var pixelCoordinates = overlayProjection.fromLatLngToDivPixel(googleCoordinates);
                    return [pixelCoordinates.x + m_left, pixelCoordinates.y + m_top];
                };

                path = d3.geo.path().projection(googleMapProjection);

                //Add the border paths for clipping
                clip.selectAll("path")
                    .data(nyc_border)
                    .attr("d", path) // update existing paths
                    .enter().append("path")
                    .attr("d", path);

                //Draw the grid paths onto the grid
                grid_group.selectAll("path")
                    .data(grid)
                    .attr("d", path) // update existing paths
                    .enter().append("path")
                    .attr("d", path)
                    .on("click", function(d) {
                        setGridLocation(d.properties.id);
                    })
                    .style("fill", function(d) {
                        var curr_loc_metric = getCurrentLocMetric(d.properties.id,
                            selected_metric);
                        var color = getColor(curr_loc_metric, selected_metric);

                        return color;
                    })
                    .style("fill-opacity", function(d) {
                        var curr_loc_metric = getCurrentLocMetric(d.properties.id,
                            selected_metric);
                        var alpha = getAlpha(curr_loc_metric, selected_metric);

                        return alpha;
                    });

            };

        };
        // Add the overlay to the map
        overlay.setMap(map);
        marker = new google.maps.Marker({map: map});

        setTimeout(function(){document.getElementById('loading').style.display = 'none';},
            2000);
    }

    /*
    JQUERY
    */

    $('#AQI_u').click(function() {
        selected_metric = 'AQI';
        document.getElementById('AQI_u').className = 'u_selected';
        document.getElementById('PM25_u').className = 'u_unselected';
        document.getElementById('O3_u').className = 'u_unselected';


        initialize();
    });
    $('#PM25_u').click(function() {
        selected_metric = 'PM25';
        document.getElementById('AQI_u').className = 'u_unselected';
        document.getElementById('PM25_u').className = 'u_selected';
        document.getElementById('O3_u').className = 'u_unselected';

        initialize();
    });
    $('#O3_u').click(function() {
        selected_metric = 'O3';
        document.getElementById('AQI_u').className = 'u_unselected';
        document.getElementById('PM25_u').className = 'u_unselected';
        document.getElementById('O3_u').className = 'u_selected';

        initialize();
    });

    //On the input box submission
    $('#location_input').on('keyup', function(e) {
        if (e.keyCode === 13) {
            var loc = document.getElementById('location_input').value;
            geocodeLocation(loc);
        }
    });

    //On current location click
    $('#geo_loc').click(function() {
        navigator.geolocation.getCurrentPosition(successFunction, errorFunction,
            {enableHighAccuracy: true});
   });

    /*
    DATA FUNCTIONS
    */

    function getCurrentLocMetric(gr_id, metric){
        var loc_dat_time = getCurrentLocData(gr_id);

        return loc_dat_time[metric];
    }

    function getCurrentLocData(gr_id){
        var loc_dat = all_grid_data.get(gr_id);

        var time = new Date();

        for(ndx=0; ndx < loc_dat.length; ndx++){
            var n_time = parseDate(loc_dat[ndx].time);
            if(time <= n_time){
                return loc_dat[ndx];
            }
        }

        return loc_dat[ndx-1];
    }

    function geocodeLocation(address){

        var out_loc = 0;
        geocoder.geocode({'address': address}, function(results, status){

            if (status == google.maps.GeocoderStatus.OK) {
                var lat = results[0].geometry.location.lat();
                var lon = results[0].geometry.location.lng();

                out_loc = setPosition(lat, lon);
            }else{
                out_loc = -1;
            }

            if(out_loc >= 0){
                document.getElementById("loc_show").innerHTML = address;
                document.getElementById("loc_show").style.color = "black";
            }else{
                //Try with tacking on NYC
                //Add on New York to narrow the location
                var address_full = address +  ', New York, NY';

                geocoder.geocode({'address': address_full}, function(results, status){

                    if (status == google.maps.GeocoderStatus.OK) {
                        var lat = results[0].geometry.location.lat();
                        var lon = results[0].geometry.location.lng();

                        setPosition(lat, lon);
                        document.getElementById("loc_show").innerHTML =
                            'defaulting to NYC search: ' + address;
                        document.getElementById("loc_show").style.color = "red";
                    }else{
                        document.getElementById("loc_show").innerHTML =
                            'Invalid location, using NYC';
                        document.getElementById("loc_show").style.color = "red";
                    }
                });
            }
        });
    }

    // On mouse click or text input submission
    function setGridLocation(gr_id){
        var loc_data = all_grid_data.get(gr_id);
        var loc_position = grid_locs[gr_id];

        setPosition(loc_position['c_lat'], loc_position['c_lon'], gr_id);

        document.getElementById("loc_show").innerHTML =
            "[" + parseFloat(loc_position['c_lat']).toFixed(2) + ", " +
                parseFloat(loc_position['c_lon']).toFixed(2) + "]";
        document.getElementById("loc_show").style.color = "black";
    }

    function setPosition(lat, lon, grid_id){
        //If grid id was not provided, get it
        if(typeof(grid_id)==='undefined'){
            grid_id = getGridId(lat, lon);
        }

        if(grid_id > -1){
            var loc_data = all_grid_data.get(grid_id);
            visualizeLocData(loc_data);

            marker.setPosition(new google.maps.LatLng([lat], [lon]));
            return grid_id;
        }else{
            return -1;
        }

    }

    function getGridId(lat, lon){
        //TODO: optimize this

        // Check each grid location sequentially
        for(ndx=0; ndx < grid_locs.length; ndx++){
            if(isInside(lat, lon, grid_locs[ndx])){
                return grid_locs[ndx]['gr_id'];
            }
        }

        //Handle case where the location is outside the grid
        // Display an error above the charts on the right, return default
        return -1;
    }

    function isInside(lat, lon, grid_loc){
        return (grid_loc.e_lon >= lon &&
                grid_loc.w_lon <= lon &&
                grid_loc.n_lat >= lat &&
                grid_loc.s_lat <= lat);
    }

    //
    // Visualization: d3 bar charts
    //

    // globals

    var margin = {top:10, right:22, bottom:45, left:38},
        outerWidth = 300,
        outerHeight = 240,
        width = outerWidth - margin.left - margin.right,
        height = outerHeight - margin.top - margin.bottom;

    // X and Y scales
    var x_scale = d3.time.scale().range([0, width]);
    var y_scale = d3.scale.linear().range([height, 0]);


    // Column charts
    function visualizeLocData(loc_data){
        var timestamps = loc_data.map(function(d){
            return parseDate(d.time);
        });

        x_scale.domain(d3.extent(timestamps));

        var barWidth = width / loc_data.length;

        d3.select("#chart_AQI").remove();
        d3.select("#chart_PM25").remove();
        d3.select("#chart_O3").remove();

        var chart_AQI = d3.select("#wrapper_AQI")
            .append("svg").attr("id", "chart_AQI");
        var chart_PM25 = d3.select("#wrapper_PM25")
            .append("svg").attr("id", "chart_PM25");
        var chart_O3 = d3.select("#wrapper_O3")
            .append("svg").attr("id", "chart_O3");

        createBarChart(chart_AQI, "AQI");
        createBarChart(chart_PM25, "PM25");
        createBarChart(chart_O3, "O3");

        function createBarChart(chart, metric){

            //TODO:
            // Scale domain based on breakpoints
            var upper_break = 10000;

            /*
            if(metric == "AQI"){
                upper_break = 500;
            }else if(metric == "PM25"){
                upper_break = 50;
            }else if(metric == "O3"){
                upper_break = 100;
            }
            */

            // Set 120% the max value found as the upper scale
            var max_value = 1.2 * Math.max.apply(null, loc_data.map(function(d) {
                return d[metric];
            }));
            if(max_value > upper_break){
                max_value = upper_break;
            }

            y_scale.domain([0, max_value]);

            // Initialize the bar chart
            chart = chart
                .attr("width", width + margin.left + margin.right)
                .attr("height", height + margin.top + margin.bottom)
                .append("g")
                .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

            // Create the groups and then the bars
            var bar = chart.selectAll("g")
                .data(loc_data)
                .enter().append("rect")
                .attr("transform", function(d, i){
                    return "translate(" + (x_scale(parseDate(d.time))) + ",0)";
                 })
                .attr("y", function(d) { return y_scale(d[metric]); })
                .attr("height", function(d) {
                    return height - y_scale(d[metric]);
                 })
                .attr("width", barWidth)
                .style("fill", function(d) {
                    var loc_metric = d[metric];
                    var color = getColor(loc_metric, metric);

                    return color;
                })
                .style("fill-opacity", function(d) {
                    var loc_metric = d[metric];
                    var alpha = getAlpha(loc_metric, metric);

                    return alpha;
                });

            // Axes
            var xAxis = d3.svg.axis()
                .scale(x_scale)
                .orient("bottom")
                .tickFormat(d3.time.format("%H:%M"));

            var yAxis = d3.svg.axis()
                .scale(y_scale)
                .orient("left");

            chart.append("g")
                .attr("class", "xAxis")
                .attr("transform", "translate(0, " + height + ")")
                .call(xAxis)
                .selectAll("text")
                .attr("dx", "-2em")
                .attr("dy", "0.5em")
                .attr("transform", "rotate(-90)");

            chart.append("g")
                .attr("class", "yAxis")
                .call(yAxis);

            var yTitle;
            if(metric == "AQI"){
                yTitle = 'AQI';
            }else if(metric == "PM25"){
                yTitle = 'PM 2.5 ug/m3LC';
            }else if(metric == "O3"){
                yTitle = 'O3 ppb';
            }

            chart.append("text")
                .attr("class", "yTitle")
                .attr("transform", "rotate(-90)")
                .attr("y", 0 - margin.left)
                .attr("x", 0 - (height / 2))
                .attr("dy", "0.8em")
                .style("font-size", "11px")
                .style("text-anchor", "middle")
                .text(yTitle);
        }
    }

    //
    // On startup
    //

    //Original initialization
    initialize();
    setPosition(40.71, -74.01);

    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(successFunction, errorFunction,
        {enableHighAccuracy: true});
    }

    //Get the latitude and the longitude;
    function successFunction(position) {
         var lat = position.coords.latitude;
         var lon = position.coords.longitude;

        setPosition(lat, lon);
    }

    function errorFunction(){
        // grid id: 287
        var lat = 40.71;
        var lon = -74.01;

        setPosition(lat, lon);
    }

    // Reinitialize on changing size
    google.maps.event.addDomListener(window, 'resize', initialize);
}


// UTILITY Date Parsing

function parseDate(input) {
    var day_parts = input.split(' ');
    var day_part = day_parts[0].split('-');
    var time_part = day_parts[1].split(':');

    // Note: months are 0-based
    var x = new Date(day_part[0], day_part[1]-1, day_part[2],
        time_part[0], time_part[1], time_part[2]);

    return x;
}
