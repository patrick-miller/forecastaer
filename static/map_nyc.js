
// Zooming and panning does not work on mobile well
// TODO: enable for desktop
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

var current_grid_data = d3.map();

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
    .defer(d3.csv, "/current_grid_data.csv", function(d) {
        current_grid_data.set(Math.round(d.gr_id), d); })
    .await(ready);

var marker;

function ready(error, nyc_border_data, grid_json, grid_locs, breakpoints){

    if (error) return console.error(error);

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
                domain.push(parseFloat(breakpoints[x].O3_1hr));
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
                console.log(breakpoints);
                val = parseFloat(breakpoints[x].O3_1hr);
            }else if(metric == "AQI"){
                val = parseFloat(breakpoints[x].Index);
            }

            if(d >= val){
                lower = val;
                if(metric == "PM25"){
                    upper = parseFloat(breakpoints[x+1].PM25_24hr);
                }else if(metric == "O3"){
                    upper = parseFloat(breakpoints[x+1].O3_1hr);
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
                        console.log(d);
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

    function geocodeLocation(address){

        //Add on New York to narrow the location
        address += ', New York, NY';

        geocoder.geocode({'address': address}, function(results, status){

            if (status == google.maps.GeocoderStatus.OK) {
                var lat = results[0].geometry.location.lat();
                var lon = results[0].geometry.location.lng();

                setPosition(lat, lon);
            }
        });

    }

    // On mouse click or text input submission
    function setGridLocation(gr_id){
        var loc_data = getLocData(gr_id);
        var loc_position = grid_locs[gr_id];

        setPosition(loc_position['c_lat'], loc_position['c_lon'], gr_id);
    }

    function getLocData(gr_id){
        return current_grid_data.get(gr_id);
    }

    function getCurrentLocMetric(gr_id, metric){
        curr_loc = getLocData(gr_id);

        return curr_loc[metric];
    }

    function setPosition(lat, lon, grid_id){
        //If grid id was not provided, get it
        if(typeof(grid_id)==='undefined'){
            grid_id = getGridId(lat, lon);
        }

        if(grid_id > -1){
            var loc_data = getLocData(grid_id);
            visualizeLocData(loc_data);

            marker.setPosition(new google.maps.LatLng([lat], [lon]));
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

        //TODO: error

        // A default grid number
        return -1;
    }

    function isInside(lat, lon, grid_loc){
        return (grid_loc.e_lon >= lon &&
                grid_loc.w_lon <= lon &&
                grid_loc.n_lat >= lat &&
                grid_loc.s_lat <= lat);
    }

    // Visualization
    function visualizeLocData(loc_data){
        //TODO: d3 bar charts

        d3.select("#curr_loc_PM25")
            .text("" + parseFloat(loc_data["PM25"]).toFixed(1));
        d3.select("#curr_loc_O3")
            .text("" + parseFloat(loc_data["O3"]).toFixed(1));
        d3.select("#curr_loc_AQI")
            .text("" + parseFloat(loc_data["AQI"]).toFixed(1));
    }

    // On startup
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

    //Original initialization
    initialize();
    google.maps.event.addDomListener(window, 'resize', initialize);
}

