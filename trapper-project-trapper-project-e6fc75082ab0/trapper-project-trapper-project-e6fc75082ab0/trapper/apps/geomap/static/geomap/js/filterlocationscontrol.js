var Trapper = (function (self) {
    return self;
}(Trapper || {}));

Trapper.Geomap = Trapper.Geomap || {};

Trapper.Geomap.utils = {
    getRadius: function (elem) {
        if (elem.__type == 'circle') {
            return elem.getRadius();
        }
        return null;
    },

    setRadius: function (elem, radius) {
        if (elem.__type == 'circle') {
            elem.setRadius(radius);
            return true;
        }
        return false;
    },

    getRadiusWithCenter: function (elem) {
        if (elem.__type == 'circle') {
            return elem.getLatLng()
                .lng + "," + elem.getLatLng()
                .lat + "," +
                elem.getRadius();
        }
        return null;
    },
    
    parseQueryString: function (query) {
        var map = {};
        query.replace(/([^&=]+)=?([^&]*)(?:&+|$)/g, function (match, key,
                                                              value) {
            (map[key] = value);
        });
        return map;
    },

};

Trapper.Geomap.FilterLocationsControl = L.Control.extend({

    options: {
        position: 'topright'
    },

    showSave: function () {
        this.saveButton.removeAttribute('disabled');
    },

    hideSave: function () {
        this.saveButton.disabled = 'disabled';
    },

    onAdd: function (map) {
        this.map = map;
        var self = this;
        var container = L.DomUtil.create('div',
                'leaflet-control-filter-locations storage-control'
            ),
            edit = L.DomUtil.create('a', '', container);
        edit.href = '#';
        edit.title = L._("Filter locations");

        L.DomEvent
            .addListener(edit, 'click', L.DomEvent.stop)
            .addListener(edit, 'click', this.openSearchUI, this);
        L.S.on('ui:startedit', function (data) {
            if (self.saveButton) {
                self.showSave();
            }
        });
        L.S.on('ui:endedit', function (data) {
            if (self.saveButton) {
                self.hideSave();
            }
        });
        return container;
    },

    openSearchUI: function (options) {
        var self = this;
        this.buildFilterLocationsContainer(options);
        L.Storage.fire("ui:start", {
            data: {
                html: this.FilterLocationsContainer
            }
        });
    },

    getTrapperLayers: function () {
        var self = this;
        var trapperLayers = [];
        for (var lay in map.datalayers) {
            var datalayer = map.datalayers[lay];
            if (datalayer.options.trapperLayer) {
                trapperLayers.push(datalayer);
            }
        }
        return trapperLayers;
    },

    buildFilterLocationsContainer: function (options) {
        var self = this;
        var container = L.DomUtil.create('div', 'filter-locations'),
            fieldset = L.DomUtil.create('fieldset', '', container),
            legend = L.DomUtil.create('legend', '', fieldset);
            inner_container = L.DomUtil.create('div',
                'filter-locations-layer-select form-inline panel', fieldset),
            selectLayer = L.DomUtil.create('select', 'form-control',
                inner_container),
            saveButton = L.DomUtil.create('button',
                'btn btn-primary', inner_container),

            saveButtonIcon = L.DomUtil.create('span',
                'glyphicon glyphicon-plus', saveButton),
            filterform = L.DomUtil.create('div',
                'filter-locations-form-div', container),

            buttonsContainer = L.DomUtil.create('div',
                'button-container',
                container),
            pointerButtonDiv = L.DomUtil.create('div',
                'col-md-2', buttonsContainer),
            pointerButton = L.DomUtil.create('button',
                'btn btn-default', pointerButtonDiv),

            bbButtonDiv = L.DomUtil.create('div',
                'col-md-2', buttonsContainer),
            bbButton = L.DomUtil.create('button',
                'btn btn-default', bbButtonDiv),

            inputGroupContainer = L.DomUtil.create('div',
                'col-md-6', buttonsContainer),
            inputGroup = L.DomUtil.create('div',
                'input-group', inputGroupContainer),
            radiusInput = L.DomUtil.create('input',
                'form-control', inputGroup),
            inputGroupBtn = L.DomUtil.create('div',
                'input-group-btn', inputGroup),
            radiusButton = L.DomUtil.create('button',
                'btn btn-default', inputGroupBtn),

            clearButtonDiv = L.DomUtil.create('div',
                'col-md-2', buttonsContainer),
            clearButton = L.DomUtil.create('button',
                'btn btn-default', clearButtonDiv),

            searchButton = L.DomUtil.create('input', '', container),
            map = this._map;
        saveButton.id = "filter_save_button_id";
        self.saveButton = saveButton;
        selectLayer.id = "filter_select_layer_id";
        radiusInput.id = "radius-input";

        var trapperLayers = this.getTrapperLayers();
        var __selected = false;
        for (var i in trapperLayers) {
            var option = L.DomUtil.create('option', '',
                selectLayer);
            option.value = i;
            option.text = trapperLayers[i].options.name;
            if (!__selected && !trapperLayers[i].options.primary) {
                option.selected = true;
                __selected = true;
            }
        }
        bbButton.type = 'button';
        bbButton.title = 'Select locations by drawing a bounding box.';
        L.DomUtil.create('span', 'glyphicon glyphicon-unchecked',
            bbButton);

        radiusButton.type = 'button';
        radiusButton.title = 'Select locations by drawing a circle. Note that you can tune a radius of this circle (in km) using provided input field.';
        L.DomUtil.create('span', 'glyphicon glyphicon-record',
            radiusButton);

        pointerButton.type = 'button';
        pointerButton.title = 'Select one or more locations.';
        L.DomUtil.create('span', 'glyphicon glyphicon-hand-up',
            pointerButton);

        clearButton.type = 'button';
        clearButton.title = 'Clear all already applied spatial filters.';
        L.DomUtil.create('span', 'glyphicon glyphicon-remove',
            clearButton);

        legend.innerHTML = L._('Choose layer');
        searchButton.type = "button";
        searchButton.value = L._('Filter');
        searchButton.className = "button";
        this.getTrapperLayers();
        document.filtered = true;
        var id = Math.random();
        map.fire('dataloading', {
            id: id
        });
        $.ajax({
            url: '/geomap/location/filterform',
            data: queryFilters,
            success: function (json) {
                if (json) {
                    filterform.innerHTML = json.location_form_html;
                    if (map.spatialFilter) {
                        var r = Trapper.Geomap.utils.getRadius(map.spatialFilter);
                    }
                    if (r) {
                        $("#radius-input").val(Number((r / 1000).toFixed(2)));
                    }
                    $("#radius-input").change(function () {
                        if (map.spatialFilter) {
                            Trapper.Geomap.utils.setRadius(map.spatialFilter,
                                                           $(this).val() * 1000);
                            $("#id_radius").val(Trapper.Geomap.utils.getRadiusWithCenter(map.spatialFilter));
                        }
                    });
                    map.fire('dataload', {
                        id: id
                    });
                }
            }
        });

        var updateMarkers = function (data) {
            var markers = trapperLayers[selectLayer.value].layer.getLayers();
            for (var i in markers) {
                if (data !== null &&
                    data.indexOf(markers[i].properties.pk.toString()) >= 0) {
                    markers[i]._select();
                } else {
                    markers[i]._deselect();
                }
            }
        };

        var fillFormFromQuery = function () {
            for (var param in document._mapParameters) {
                var value = document._mapParameters[param];
                if (param == 'pk') {
                    value = value.split(",");
                    $('#id_pk').val(value);
                } else {
                    $('#filter-locations-form')
                        .find('[name="' + param + '"]')
                        .val(value);
                }
            }
        };

        var refreshRemoteLayers = function () {

            var remoteURL;
            // get filter-locations-form and serialize it
            var filterform_serialized = $(
                '.filter-locations-form-div form')
                .serializeArray();
            var selectedLayer = trapperLayers[selectLayer.value];

            remoteURL = selectedLayer.options.remoteData.url;
            // add filter parameters
            var _filtered = {};
            for (var j in filterform_serialized) {
                var name = filterform_serialized[j].name;
                var value = filterform_serialized[j].value;
                if (!_filtered[name]) {
                    _filtered[name] = {
                        name: name,
                        value: value
                    };
                } else {
                    _filtered[name].value += "," + value;
                }
            }
            if (!_filtered.pk) {
                _filtered.pk = {
                    name: "pk",
                    value: ""
                };
            }
            for (var k in _filtered) {
                remoteURL = updateURLQueryParam(
                    _filtered[k].name,
                    _filtered[k].value,
                    remoteURL);
                queryFilters[_filtered[k].name] =
                    _filtered[k].value;
            }
            selectedLayer.options.remoteData.url =
                remoteURL;
            if (selectedLayer.options.clearToPrimary) {
                selectedLayer.options.clearToPrimary = false;
                selectedLayer.options.remoteData.url = selectedLayer.options.primaryURL;
            }
            selectedLayer.fetchRemoteData();
            if (!selectedLayer.options.primary) {
                selectedLayer.isDirty = true;
            }

            for (var property in queryFilters) {
                if (queryFilters.hasOwnProperty(property)) {
                    queryFiltersResource[property.split('__')[
                        1]] = queryFilters[property];
                }
            }
        };

        var fireSaveEvent = function () {
            L.S.fire('ui:saveprimary', {
                map: map
            });
        };

        var clearSelection = function () {
            var selectedLayer = trapperLayers[selectLayer.value];
            if (map.spatialFilter) {
                map.spatialFilter.del();
            }
            var markers = selectedLayer.layer.getLayers();
            for (var i in markers) {
                markers[i]._deselect();
            };

            var params;
            var url = selectedLayer.options.remoteData
                .url;
            if (selectedLayer.options.primaryURL) {
                selectedLayer.options.clearToPrimary = true;
            }

            params = url.split('?')[1];
            url = url.split("?")[0];

            params = Trapper.Geomap.utils.parseQueryString(params);
            delete params.in_bbox;
            delete params.radius;
            delete params.locations_map;

            for (var param in params) {
                url = updateURLQueryParam(param, params[
                    param], url);
            }
            $('#id_radius')
                .val('');
            $("#radius-input")
                .val('');
            $('#id_in_bbox')
                .val('');
            $('#id_locations_map')
                .val('');
            selectedLayer.options.remoteData.url =
                url;
        };

        var addToSelect = function (e) {
            var map = e.target.map
            var element = e.target

            if (map.spatialFilter && map.spatialFilter != element) {
                map.spatialFilter.del();
            }
            map.spatialFilter = element;

            $('#id_in_bbox')
                .val('');
            $('#id_radius')
                .val('');
            switch (element.__type) {
            case 'rectangle':
                $("#id_in_bbox")
                    .val(element.getBounds()
                         .toBBoxString());
                break;
            case 'circle':
                $("#id_radius")
                    .val(element.getLatLng()
                         .lng + "," + element.getLatLng()
                         .lat + "," +
                         element.getRadius());
                $("#radius-input")
                    .val(Number((element.getRadius() / 1000).toFixed(2)));
                break;
            default:
                break;
            }
        };
        
        var radiusSelect = function (data) {
            var circle = map.editTools.startCircle()
            circle.__type = "circle";
            circle.on('editable:vertex:dragend', addToSelect);
        };

        var bboxSelect = function (data) {
            var rect = map.editTools.startRectangle()
            rect.__type = "rectangle";
            rect.on('editable:vertex:dragend', addToSelect);
        };

        var togglePointerSelection = function (data) {
            if (document.pointerSelection) {
                document.pointerSelection = false;
                $(pointerButton)
                    .removeClass("active");
            } else {
                document.pointerSelection = true;
                $(pointerButton)
                    .addClass("active");
            }
        };
        L.DomEvent
            .addListener(searchButton, 'click', L.DomEvent.stop)
            .addListener(searchButton, 'click',
            refreshRemoteLayers, this);

        L.DomEvent
            .addListener(saveButton, 'click', L.DomEvent.stop)
            .addListener(saveButton, 'click', fireSaveEvent, this);

        L.DomEvent
            .addListener(bbButton, 'click', L.DomEvent.stop)
            .addListener(bbButton, 'click', bboxSelect, this);

        L.DomEvent
            .addListener(radiusButton, 'click', L.DomEvent.stop)
            .addListener(radiusButton, 'click', radiusSelect, this);

        L.DomEvent
            .addListener(clearButton, 'click', L.DomEvent.stop)
            .addListener(clearButton, 'click', clearSelection,
            this);

        L.DomEvent
            .addListener(pointerButton, 'click', L.DomEvent.stop)
            .addListener(pointerButton, 'click',
            togglePointerSelection,
            this);
        this.FilterLocationsContainer = container;

    },
});

Trapper.Geomap.ClearFiltersControl = L.Control.extend({

    options: {
        position: 'topright'
    },

    onAdd: function (map) {
        var container = L.DomUtil.create('div',
                'leaflet-control-clear-filters-locations storage-control'
            ),
            edit = L.DomUtil.create('a', '', container);
        edit.href = '#';
        edit.title = L._("Show all (clear filtering)");

        L.DomEvent
            .addListener(edit, 'click', L.DomEvent.stop)
            .addListener(edit, 'click', this.clearFilters, this);
        this.map = map;
        return container;
    },

    clearFilters: function (options) {
        this.map.primary_layer.options.remoteData.url = this.map._base_trapper_url;
        this.map.primary_layer.fetchRemoteData();
        if (this._map.spatialFilter) {
            this._map.spatialFilter.del();
        }
        queryFilters = {};
        L.Storage.fire("ui:end");
        document._mapParameters = {};

        L.Storage.fire("ui:alert", {
            content: L._("Filters cleared"),
            level: 'info'
        });
    },
});

Trapper.Geomap.BackToClassifications = L.Control.extend({
    options: {
        position: 'topleft',
        projects: []
    },

    onAdd: function (map) {
        this._initLayout();
        this.map = map;
        return this._container;
    },

    _getMakersFromVisible: function () {
        var pks = [];
        var prim_layer = this.map.primary_layer.layer.getLayers();
        for (var i in prim_layer) {
            pks.push(prim_layer[i].properties.pk);
        }
        for (var j in this.map.datalayers) {
            var layer = this.map.datalayers[j];
            if (layer.options.trapperLayer && layer.isVisible()) {
                var _layer = layer.layer.getLayers();
                for (var midx in _layer) {
                    var marker = _layer[midx];
                    if (pks.indexOf(marker.properties.pk) < 0) {
                        pks.push(marker.properties.pk);
                    }
                }
            }
        }
        return pks;
    },

    createEvents: function () {
        var self = this;
        $("#select-researchproject-map").on('change', function () {
            var val = $(this).val();
            if (val) {
                var pks = self._getMakersFromVisible();
                localStorage.setItem("trapper.geomap.locations", pks.join(","));
                localStorage.setItem("trapper.geomap.locations_filter", JSON.stringify(pks));
                localStorage.setItem('trapper.geomap.source', 'classifications');
                window.location.assign('/media_classification/classification/list/' + val + '/');
            }
            else {
                $('#class-select-container').addClass('hidden');
            }
        });
    },

    _initLayout: function () {
        var container = this._container = L.DomUtil.create('div', 'class-projects-container');
        var button = L.DomUtil.create('div',
                ' leaflet-control-back-to-' +
                this.options.backto + ' storage-control', container),
            edit = L.DomUtil.create('a', '', button);
        edit.href = '#';
        edit.title = L._("Back to classifications (keep filtering)");
        var className = 'classificationsControl hidden';
        var select_container = this._container = L.DomUtil.create('div', className, container);
        select_container.id = "class-select-container";
        this._baseLayersList = L.DomUtil.create('div', className + '-base');
        select_container.appendChild(this._baseLayersList);

        this._baseLayerDropDown = L.DomUtil.create('div', 'classificationsDropDown', this._baseLayersList);
        var select = L.DomUtil.create('select', '', this._baseLayerDropDown);
        select.id = "select-researchproject-map";
        var option = L.DomUtil.create('option', '', select);
        option.value = '';
        option.innerHTML = L._('Select project');
        for (var i in this.options.projects) {
            option = L.DomUtil.create('option', '', select);
            option.value = this.options.projects[i].id;
            option.innerHTML = this.options.projects[i].name;
        }
        this._baseLayerDropDown.firstChild.onmousedown = this._baseLayerDropDown.firstChild.ondblclick = L.DomEvent.stopPropagation;

        L.DomEvent
            .addListener(edit, 'click', L.DomEvent.stop)
            .addListener(edit, 'click', function () {
                if (L.DomUtil.hasClass(select_container, 'hidden')) {
                    L.DomUtil.removeClass(select_container, 'hidden');
                } else {
                    L.DomUtil.addClass(select_container, 'hidden');
                }
            }, this);

        this._container = container;
    },
});

Trapper.Geomap.BackToTrapper = L.Control.extend({

    options: {
        position: 'topleft',
        backto: 'locations'
    },

    onAdd: function (map) {
        var container = L.DomUtil.create('div',
                ' leaflet-control-back-to-' +
                this.options.backto + ' storage-control'
            ),
            edit = L.DomUtil.create('a', '', container);
        edit.href = '#';
        switch (this.options.backto) {
            case 'locations':
                edit.title = L._("Back to locations (keep filtering)");
                break;
            case 'resources':
                edit.title = L._("Back to resources (keep filtering)");
                break;
            case 'collections':
                edit.title = L._("Back to collections (keep filtering)");
                break;
            case 'classifications':
                edit.title = L._("Back to classifications (keep filtering)");
                break;
        }

        this.map = map;
        L.DomEvent
            .addListener(edit, 'click', L.DomEvent.stop)
            .addListener(edit, 'click', this.back, this);
        return container;
    },

    _getMakersFromVisible: function () {
        var pks = [];
        var prim_layer = this.map.primary_layer.layer.getLayers();
        for (var i in prim_layer) {
            pks.push(prim_layer[i].properties.pk);
        }
        for (var j in this.map.datalayers) {
            var layer = this.map.datalayers[j];
            if (layer.options.trapperLayer && layer.isVisible()) {
                var _layer = layer.layer.getLayers();
                for (var midx in _layer) {
                    var marker = _layer[midx];
                    if (pks.indexOf(marker.properties.pk) < 0) {
                        pks.push(marker.properties.pk);
                    }
                }
            }
        }
        return pks;
    },

    back: function (options) {
        // only location for now
        var layer = this.map.primary_layer.layer.getLayers();
        var pks = this._getMakersFromVisible();
        localStorage.setItem("trapper.geomap.locations", pks.join(","));
        localStorage.setItem("trapper.geomap.locations_filter", JSON.stringify(pks));
        localStorage.setItem("trapper.geomap.exclude_filters",
            JSON.stringify(this.map._filters));
        localStorage.setItem('trapper.geomap.source', this.options.backto);
        switch (this.options.backto) {
            case 'locations':
                window.location.assign('/geomap/location/list/');
                break;
            case 'resources':
                window.location.assign('/storage/resource/list/');
                break;
            case 'collections':
                window.location.assign('/storage/collection/list/');
                break;
            case 'classifications':
                window.location.assign('/media_classification/classification/list/');
                break;
        }
    },
});
