
// Zooming and panning does not work on mobile well
// TODO: enable for desktop

var m_top = 4000,
    m_left = 4000,
    center_lat = 40.71,
    center_lon = -73.98,
    se_bound = new google.maps.LatLng(40.49, -74.31),
    nw_bound = new google.maps.LatLng(40.84, -73.75);

var mapOptions = {
    draggableCursor: 'crosshair',

    zoom: 10,
    center: new google.maps.LatLng(center_lat, center_lon),
    //mapTypeId: google.maps.MapTypeId.TERRAIN,
    mapTypeId: google.maps.MapTypeId.ROADMAP,
    minZoom: 9  //NYC centric

    /*
    panControl: false,
    zoomControl: false,
    mapTypeControl: false,
    scaleControl: false,
    streetViewControl: false,
    overviewMapControl: false,
    rotateControl: false,
    disableDoubleClickZoom: true,
    scrollwheel: false,
    draggable: false,
    keyboardShortcuts: false
    */
};

var current_loc_data = d3.map();


// Queue up the data files
queue()
    .defer(d3.json, "/static/nyc_border.geojson")
    .defer(d3.json, "/static/grid.geojson")
    .defer(d3.csv, "/static/breakpoints.csv")
    .defer(d3.csv, "/static/current_loc_data.csv", function(d) { current_loc_data.set(Math.round(d.gr_id), d); })
    .await(ready);


function ready(error, nyc_border_data, grid_data, breakpoints){

    if (error) return console.error(error);

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

        var domain = [];

        for(x = 0; x < breakpoints.length; x++){

            if(metric == "PM25"){
                domain.push(parseFloat(breakpoints[x].PM25_24hr));
            }else if(metric == "O3"){
                domain.push(parseFloat(breakpoints[x].O3_1hr));
            }else if(metric == "AQI"){
                domain.push(parseFloat(breakpoints[x].Index));
            }

        }

        var alpha = d3.scale.linear().domain(domain).range([0.3, 0.9]);

        return alpha(d);
    }



    var nyc_border = nyc_border_data.features;

    // Load the google map
    function initialize() {

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

            var grid = grid_data.features;

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
                    .on("mouseover", function(d) {
                        outputLocInfo(d);
                    })
                    .on("click", function(d) {
                        outputLocInfo(d);
                    })
                    .style("fill", function(d) {
                        var metric = "PM25";
                        var curr_loc_metric = getCurrentLocMetric(d, metric);
                        var color = getColor(curr_loc_metric, metric);

                        return color;
                    })
                    .style("fill-opacity", function(d) {
                        var metric = "PM25";
                        var curr_loc_metric = getCurrentLocMetric(d, metric);
                        var alpha = getAlpha(curr_loc_metric, metric);

                        return alpha;
                    });

            };

        };
        // Add the overlay to the map
        overlay.setMap(map);

    }
    initialize();
    google.maps.event.addDomListener(window, 'resize', initialize);
}

var highlighted_loc;
// On mouse over of a location
function outputLocInfo(d){

    highlighted_loc = getLocData(d);

    d3.select("#curr_loc_PM25")
        .text("" + parseFloat(highlighted_loc["PM25"]).toFixed(1));
    d3.select("#curr_loc_O3")
        .text("" + parseFloat(highlighted_loc["O3"]).toFixed(1));
    d3.select("#curr_loc_AQI")
        .text("" + parseFloat(highlighted_loc["AQI"]).toFixed(1));
}

function getLocData(d){
    return current_loc_data.get(d.properties.id);
}

function getCurrentLocMetric(d, metric){
    curr_loc = getLocData(d);

    return curr_loc[metric];
}



var my_lat;
var my_lon;

if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(successFunction, errorFunction, {enableHighAccuracy: true});
}

//Get the latitude and the longitude;
function successFunction(position) {
     my_lat = position.coords.latitude;
     my_lon = position.coords.longitude;

    document.getElementById('my_loc_lat').textContent = my_lat.toFixed(2);
    document.getElementById('my_loc_lon').textContent = my_lon.toFixed(2);
}

function errorFunction(){
    alert("Geolocation failed");
}


