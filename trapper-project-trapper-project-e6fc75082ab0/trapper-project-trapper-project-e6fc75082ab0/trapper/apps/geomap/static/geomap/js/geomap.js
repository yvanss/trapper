var parseQueryString = function () {
    var query = (location.search || '?')
        .substr(1),
    map = {};
    query.replace(/([^&=]+)=?([^&]*)(?:&+|$)/g, function (match, key,
                                                          value) {
        (map[key] = value);
    });
    return map;
};

var updateURLQueryParam = function (param, newval, url) {
    var urlParts = url.split('?');
    if (!urlParts[1]) {
        return [urlParts[0], '?', param, '=', newval].join('');
    }
    var regex = RegExp('([?|&])' + param + '=([^&]*)')
        .exec(urlParts[1]);
    if (regex) {
        return url.replace([param, '=', regex[2]].join(''), [param, '=',
            newval
        ].join(''));
    } else {
        return [url, '&', param, '=', newval].join('');
    }
};

var clearURLQueryParam = function (url) {
    var urlParts = url.split('?');
    return urlParts[0];
};

var clearLocalStorage = function () {
    localStorage.removeItem('trapper.geomap.source');
    localStorage.removeItem('trapper.geomap.filter');
    localStorage.removeItem('trapper.geomap.collections_names');
};

/**
 * Get combined bounding box for all visible layers
 * @param  {Array} datalayers
 * @return {L.Bounds}
 */
var getCombinedBounds = function (datalayers, MAP) {
    var main_bounds;
    var bounds;
    for (var lay in datalayers) {
        var layer = datalayers[lay].layer;
        if (layer && datalayers[lay].isLoaded() &&
            datalayers[lay].isVisible()) {
            bounds = layer.getBounds();
            if (bounds.isValid()) {
                if (main_bounds) {
                    main_bounds.extend(bounds._northEast);
                    main_bounds.extend(bounds._southWest);
                } else {
                    main_bounds = bounds;
                }
            }
        }
    }
    return main_bounds;
};

var _pointToLayer = function (geojson, latlng) {
    var marker = new Trapper.Geomap.Marker(
        document.MAP,
        latlng, {
            "geojson": geojson,
            "draggable": false,
        }
    );
    var values = $("#id_locations_map").val();
    if (!values) {
        values = [];
    }
    if (values.indexOf(marker.properties.pk.toString()) >= 0) {
        if (!marker.selected) {
            marker.selected = true;
        }
    }
    return marker;
};

var _fetchRemoteData = L.Storage.DataLayer.prototype.fetchRemoteData;
L.Storage.DataLayer.prototype.fetchRemoteData = function () {
    if (this.options.trapperLayer) {
        if (!this.options.primary && !this.options.primaryURL) {
            this.options.primaryURL = this.options.remoteData.url;

        }
        this.options.pointToLayer = _pointToLayer;
    }
    _fetchRemoteData.apply(this);
};

var defaultOptions = {
    displayOnLoad: true,
    iconClass: "Drop",
    markercluster: true,
    trapperLayer: true,
    pointToLayer: _pointToLayer,
};

/**
 * Creates primary Trapper layer to be used as template for
 * creation of new layers
 * @param  {L.Map} map
 * @return {L.Storage.DataLayer} (unbound)
 */
var createPrimaryLayer = function (map, params, clear) {
    var url = "/geomap/api/locations/geojson/?format=json";
    map._base_trapper_url = url;
    if (clear) {
        url = url + "&locations_map=-1";
    } else {
        if (params.action && params.action == "create") {
            url = url + "&locations_map=-1";
        } else {
            for (var param in params) {
                url = updateURLQueryParam(param, params[param], url);
            }
        }
    }
    var color = "#c00";
    var options = {
        color: color,
        fillColor: color,
        primary: true,
        name: L._("Default"),
        remoteData: {
            dynamic: false,
            format: "geojson",
            url: url
        },
    };
    options = L.extend(options, defaultOptions);
    var primary_layer = new L.Storage.DataLayer(map, options);
    primary_layer.isDirty = false;
    return primary_layer;
};

var createCollectionLayer = function (collection_id, collection_name) {
    var color = Utk.ColorUtils.randomColor("#AAA");
    var url = "/geomap/api/locations/geojson/?format=json";
    //MAP._base_trapper_url = url;
    url = updateURLQueryParam('colls', collection_id, url);
    var name = "Collection " + collection_id;
    if (collection_name) {
        name = collection_name;
    }
    var options = {
        name: name,
        color: color,
        fillColor: color,
        remoteData: {
            dynamic: false,
            format: 'geojson',
            url: url,
        }
    };
    options = L.extend(options, defaultOptions);
    var newTrapperLayer = new L.Storage.DataLayer(MAP, options);
    newTrapperLayer.fetchRemoteData();
};

var savePrimary = function (data) {
    var color = Utk.ColorUtils.randomColor("#CCC");
    var options = {
        name: "Trapper " + (parseInt(data.map.datalayers_index.length) +
        1),
        color: color,
        fillColor: color,
        remoteData: {
            dynamic: false,
            format: 'geojson',
            url: MAP.primary_layer.options.remoteData.url,
        }
    };
    options = L.extend(options, defaultOptions);
    var newTrapperLayer = new L.Storage.DataLayer(data.map, options);
    newTrapperLayer.fetchRemoteData();
    L.S.fire('ui:alert', {
        content: L._(
            'You have successfully added a new layer.'),
        level: 'info'
    });

};

var count = 0,
    countVisible = 0;
$(document)
    .ready(function () {

        window.onbeforeunload = null;
        MAP.disableEdit();

        document._mapParameters = parseQueryString();
        if (document._mapParameters.action == "full" || 
            document._mapParameters.action == "create" || 
            document._mapParameters.edit == "true") {
            clearLocalStorage();
        }

        MAP.addControl(new Trapper.Geomap.BackToTrapper({
            backto: 'locations'
        }));
        MAP.addControl(new Trapper.Geomap.BackToTrapper({
            backto: 'resources'
        }));
        MAP.addControl(new Trapper.Geomap.BackToTrapper({
            backto: 'collections'
        }));
        var backToClassifications = new Trapper.Geomap.BackToClassifications({
            projects: classification_projects,
            backto: 'classifications'
        });
        MAP.addControl(backToClassifications);
        backToClassifications.createEvents();
        MAP.filterLocationsControl = new Trapper.Geomap.FilterLocationsControl();
        MAP.addControl(MAP.filterLocationsControl);
        MAP.addControl(new Trapper.Geomap.ClearFiltersControl());

        MAP._filters = {
            collections: {},
            resources: {},
            classifications: {},
        };

        MAP.modifyMarkerTrapperControl = new Trapper.Geomap.ModifyTrapperMarkerControl();
        MAP.createMarkerTrapperControl = new Trapper.Geomap.CreateTrapperMarkerControl();

        window.queryFilters = parseQueryString();
        window.queryFiltersResource = {};

        document.MAP = MAP;

        for (var property in queryFilters) {
            if (queryFilters.hasOwnProperty(property)) {
                queryFiltersResource[property.split('__')[1]] =
                    queryFilters[property];
            }
        }

        var addTrapperLayer = function (layerName, options) {
            var layer = MAP._createDataLayer({
                name: L._(layerName)
            });
            $.extend(layer.options, options);
            layer.resetLayer();
            layer.fetchRemoteData();
            return layer;
        };
        var collections_names;
        var clear = false;
        if (window.object) {
            clear = true;
        }
        var filter_data = JSON.parse(localStorage.getItem('trapper.geomap.filter'));
        var filter_data_str = "";
        if (filter_data) {
            filter_data_str = filter_data.join();
        }
        switch (localStorage.getItem("trapper.geomap.source")) {
            case "resources":
                document._mapParameters.reses = filter_data_str;
                clear = false;
                sType = localStorage.getItem("trapper.geomap.source");
                break;
            case "collections":
                document._mapParameters.colls = filter_data_str;
                var _collections_names = localStorage.getItem('trapper.geomap.collections_names');
                collections_names = JSON.parse(_collections_names);
                sType = localStorage.getItem("trapper.geomap.source");
                break;
            case "classifications":
                document._mapParameters.classes = filter_data_str;
                clear = false;
                sType = localStorage.getItem("trapper.geomap.source");
                break;
            case "locations":
                document._mapParameters.locations = filter_data_str;
                clear = false;
                break;
            case "deployments":
                document._mapParameters.deployments = filter_data_str;
                clear = false;
                break;
        }

        if (localStorage.getItem('trapper.geomap.source') === 'collections') {
            if (document._mapParameters.colls) {
                var colls = document._mapParameters.colls.split(",");
                for (var i in colls) {
                    createCollectionLayer(colls[i], collections_names[colls[i]]);
                    clear = true;
                }
            }
        }

        if (!MAP.primary_layer) {
            MAP.primary_layer = createPrimaryLayer(MAP,
                document._mapParameters, clear);
            MAP.primary_layer.fetchRemoteData();
        }

        if (document._mapParameters.action &&
            document._mapParameters.action == "create") {
            MAP.createMarkerTrapperControl.openMarkerUI();
            MAP.on('click', Trapper.Geomap._mapClicked);
        }

        L.S.on("ui:start", function (data) {
            var options = {
                valueNames: ['resources_name', 'resources_desc']
            };
            var userList = new List('resources_id', options);
        });

        L.S.on("ui:saveprimary", savePrimary);
        L.S.on("ui:end", function () {
            document.pointerSelection = false;
        });
        L.S.on("ui:start", function () {
            document.pointerSelection = false;
        });

        var updateZoom = function (data) {
            var bounds = getCombinedBounds(MAP.datalayers, MAP);
            if (bounds && bounds.isValid()) {
                MAP.fitBounds(bounds, {
                    maxZoom: 15
                });
                $("#id_locations_map").change();
            }
        };

        for (var lay in MAP.datalayers) {
            layer = MAP.datalayers[lay];
            if (layer.isVisible()) {
                countVisible += 1;
            }
            layer.on("dataloaded", updateZoom);
        }

        var editMarker = function() {
            var marker = MAP.primary_layer.layer.getLayers()[0];
            marker.edit();
        }

        if (document._mapParameters.edit && 
            document._mapParameters.edit == "true") {
            MAP.primary_layer.on('dataloaded', editMarker);
        }

    });
