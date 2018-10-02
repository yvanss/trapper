var Trapper = (function (self) {
    return self;
}(Trapper || {}));

Trapper.Geomap = Trapper.Geomap || {};

Trapper.Geomap.Marker = L.Storage.Marker.extend({
    _this_marker: this,

    addInteractions: function () {
        L.Storage.FeatureMixin.addInteractions.call(this);
        this.on("dragstart", function (e) {
            return
        });
    },
    
    _moveMarker: function (lat, lng) {
        var latLng = L.latLng(lat, lng);
        this.setLatLng(latLng);
        this.map.panTo(latLng);
        $("#id_coordinates")
            .val(this._getWKT());
    },

    toggleSelect: function () {
        // var icon_jq = $(this._icon);
        if (!this.oldColor) {
            this.oldColor = this.options.icon._getColor();
        }
        if (this.selected) {
            this._deselect();
        } else {
            this._select();
        }
    },

    _deselect: function () {
        this.selected = false;
        this.color = this.oldColor;
        try {
            this.options.icon._setColor();
        } catch (e) {
            // TODO: Ay Ay Ay Ay!
        }
    },

    _select: function () {
        this.selected = true;
        this.color = "#FFFF33";
        try {
            this.options.icon._setColor();
        } catch (e) {
            // TODO: Ay Ay Ay Ay!
        }
    },

    _clearSelected: function () {
        this.datalayer.eachLayer(function (data) {
            if (data._selected) {
                data._selected = false;
                data.options.icon.options.iconUrl = data._oldIcon;
                data.options.icon.elements.img.src = data.options.icon._getIconUrl('icon');
            }
        });
    },

    _selectOne: function () {
        this._selected = true;
        this._oldIcon = this.options.icon.options.iconUrl;
        this.options.icon.options.iconUrl = '/static/geomap/img/dot.png';
        this.options.icon.elements.img.src = this.options.icon._getIconUrl('icon');
    },

    _clearSelect: function () {
        this.datalayer.eachLayer(function (data) {
            if (data.selected) {
                data.selected = false;
                data.color = data.oldColor;
                try {
                    this.options.icon._setColor();
                } catch (e) {

                }
            }
        });
    },

    _initIcon: function () {
        this.options.icon = this.getIcon();
        L.Marker.prototype._initIcon.call(this);
        if (!this.oldColor) {
            this.oldColor = this.options.icon._getColor();
        }
    },

    view: function (e) {
        if (document.pointerSelection) {
            var values = $('#id_locations_map').val().split(',');
            if (this.selected) {
                this.toggleSelect();
                var index = values.indexOf(this.properties.pk.toString());
                if (index > -1) {
                    values.splice(index, 1);
                }
                $('#id_locations_map').val(values.join());
            } else {
                this.toggleSelect();
                values.push(this.properties.pk.toString());
                $('#id_locations_map').val(values.join());
            }
        } else {
            if (this._selected) {
                L.S.fire("ui:end", {});
                this._clearSelected();
            } else {
                this._clearSelected();
                this._selectOne();
                var url = '/geomap/location/' + this.properties.pk +
                    '/';
                L.Storage.fire("ui:start", {
                    data: {
                        html: this._buildMarkerDetailsPanel()
                    }
                });
            }
        }
    },

    edit: function (e) {
        if (MAP.createMarkerTrapperControl.create_marker) {
            MAP.removeLayer(MAP.createMarkerTrapperControl.create_marker);
            MAP.createMarkerTrapperControl.create_marker = null;
        }
        this._clearSelected();
        var location_id = this.properties.pk;
        MAP.modifyMarkerTrapperControl.openMarkerUI({
            location_id: location_id,
            marker: this
        });
        MAP.on('click', Trapper.Geomap._mapClicked);
        this._selectOne();
        L.S.fire('ui:alert', {
            content: 'Click on the map to select a new location.',
            level: 'info'
        });
    },

    _getWKT: function () {
        var latLng = this.getLatLng();
        return "POINT (" + latLng.lng + " " + latLng.lat + ")";
    },

    _buildMarkerDetailsPanel: function () {
        setTimeout(function () {
            document.querySelector('#storage-ui-container').classList.add('gm-plain-container');
        }, 0);

        var container = L.DomUtil.create('div', 'view-location gm-item'),
            title = L.DomUtil.create('h2', 'gm-title', container),
            details = L.DomUtil.create('ul', 'gm-details', container),
            name = L.DomUtil.create('li', 'gm-name', details),
            latLbl = L.DomUtil.create('li', 'gm-latlabel', details),
            lngLbl = L.DomUtil.create('li', 'gm-lnglabel', details),
            desc = L.DomUtil.create('li', 'gm-desc', details),

            navTabs = L.DomUtil.create('ul', 'nav nav-tabs gm-menu', container),
            resTab = L.DomUtil.create('li', '', navTabs),
            resBtn = L.DomUtil.create('a', '', resTab),
            colTab = L.DomUtil.create('li', '', navTabs),
            colBtn = L.DomUtil.create('a', '', colTab),
            clasTab = L.DomUtil.create('li', '', navTabs),
            clasBtn = L.DomUtil.create('a', '', clasTab),

            innerContainer = L.DomUtil.create('div', 'gm-subitems', container);

        var self = this;

        title.innerHTML = this.properties.location_id;
        name.innerHTML = '<span>' + L._('Name') + ':</span> ' + (this.properties.name || '');
        desc.innerHTML = '<span>' + L._('Description') + ':</span> ' + (this.properties.description || '');
        latLbl.innerHTML = '<span>' + L._('Latitude') + ":</span> " + this.getLatLng().lat;
        lngLbl.innerHTML = '<span>' + L._('Longitude') + ":</span> " + this.getLatLng().lng;

        resBtn.innerHTML = L._('Resources');
        colBtn.innerHTML = L._('Collections');
        clasBtn.innerHTML = L._('Classifications');

        innerContainer.innerHTML = "<p class=\"gm-info\">select data type first</p>";

        var _clearActive = function () {
            L.DomUtil.removeClass(resTab, 'active');
            L.DomUtil.removeClass(colTab, 'active');
            L.DomUtil.removeClass(clasTab, 'active');
            innerContainer.innerHTML = "<p class=\"gm-info\">select data type first</p>";
        };

        var _buildFilter = function (container) {
            // search filter
            var input = L.DomUtil.create(
                'input', 
                'search form-control gm-search',
                container
            );
            input.placeholder = 'Search';
        };

        var _buildClassificationSelect = function (container, data) {
            var row = L.DomUtil.create('div', 'form-inline gm-filters', container);
            var div_cont = L.DomUtil.create('div', 'form-group', row);
            var select = L.DomUtil.create('select', '', div_cont);
            select.id = 'select-clas-project-loc';
            var option = L.DomUtil.create('option', '', select);
            option.innerHTML = L._("Choose Classification Project");

            option.value = '';
            for (var i in data) {
                console.log(data);
                option = L.DomUtil.create('option', '', select);
                option.value = data[i].id;
                option.innerHTML = data[i].name;
            }
        };

        var getType = function(name) {
            if(name) {
                var types = {
                    'a': 'Audio',
                    'v': 'Video',
                    'i': 'Image'
                };
                return types[name.toLowerCase()];   
            } else {
                return 'undefined';
                }   
        };

        var _buildResource = function (resource, container) {

            var li = L.DomUtil.create('li', '', container),
                name = L.DomUtil.create('h3', 's-name', li),
                href_name = L.DomUtil.create('a', 'pull-right', li),
                href = L.DomUtil.create('a', 'gm-media', li),
                img = L.DomUtil.create('img', '', href),
                details = L.DomUtil.create('ul', 'gm-details', li),
                type = L.DomUtil.create('li', '', details),
                dates = L.DomUtil.create('li', '', details),
                deployment = L.DomUtil.create('li', 's-deployment', details),
                tags = L.DomUtil.create('li', 'hidden tags s-tags', details),
                description = L.DomUtil.create('li', 'hidden desc s-desc', details);

            name.innerHTML = resource.name;
            href_name.href = '/storage/resource/detail/' + resource.pk + '/';
            href_name.target = '_blank';
            if (resource.thumbnail_url) {
                href.href = '/storage/resource/detail/' + resource.pk + '/';
                href.target = '_blank';
                img.src = resource.thumbnail_url;
            } else {
                li.removeChild(href);
                li.classList.add('gm-no-media');
            }

            tags.innerHTML = '<span>' + L._('Tags') + ":</span> " + resource.tags.join(",");
            description.innerHTML = '<span>' + L._('Description') + ":</span> " + resource.description;
            dates.innerHTML = '<span>' + L._('Recorded') + ":</span> " + moment(resource.date_recorded).format("DD.MM.YYYY, HH:MM");
            type.innerHTML = '<span>' + L._('Type') + ":</span> " + getType(resource.resource_type);
            deployment.innerHTML = '<span>' + L._('Deployment') + ":</span> " + resource.deployment; 
        };

        var _buildCollection = function (collection, container) {
            var li = L.DomUtil.create('li', 'gm-no-media', container),
                name = L.DomUtil.create('h3', 's-name', li),
                href_name = L.DomUtil.create('a', '', name),
                details = L.DomUtil.create('ul', 'gm-details', li),
                status = L.DomUtil.create('li', '', details),
                dates = L.DomUtil.create('li', '', details);

            href_name.href = '/storage/collection/detail/' + collection.pk + '/';
            href_name.target = '_blank';
            href_name.innerHTML = collection.name;
            dates.innerHTML = '<span>' + L._('Created') + ":</span> " + moment(collection.date_created).format("DD.MM.YYYY, HH:MM");
            status.innerHTML = '<span>' + L._('Status') + ":</span> " + collection.status;
        };

        var _buildClassification = function (resource, container) {
            var li = L.DomUtil.create('li', '', container),
                name = L.DomUtil.create('h3', 's-name', li),
                href = L.DomUtil.create('a', 'gm-media', li),
                img = L.DomUtil.create('img', '', href),
                details = L.DomUtil.create('ul', 'gm-details', li),
                type = L.DomUtil.create('li', '', details),
                dates = L.DomUtil.create('li', '', details),
                deployment = L.DomUtil.create('li', 's-deployment', details),
                description = L.DomUtil.create('li', 'hidden desc s-desc', details),
                dyna_attrs = L.DomUtil.create('li', 'hidden dyna_attrs s-dyna_attrs', details),
                static_attrs = L.DomUtil.create('li', 'hidden static_attrs s-stat_attrs', details),
                clas_project = L.DomUtil.create('li', 'hidden clas_project s-clas_project', details);

            name.innerHTML = resource.resource.name;
            dates.innerHTML = '<span>' + L._('Recorded') + ":</span> " + 
                moment(resource.resource.date_recorded).format("DD.MM.YYYY, HH:MM");
            type.innerHTML = '<span>' + L._('Type') + ":</span> " + 
                getType(resource.resource.resource_type);
            deployment.innerHTML = '<span>' + L._('Deployment') + ":</span> " + 
                resource.resource.deployment; 

            if (resource.resource.thumbnail_url) {
                href.href = resource.classify_data;
                href.target = '_blank';
                img.src = resource.resource.thumbnail_url;
            } else {
                li.removeChild(href);
                li.classList.add('gm-no-media');
            }

            description.innerHTML = resource.resource.description;
            static_attrs.innerHTML = JSON.stringify(resource.static_attrs);
            dyna_attrs.innerHTML = JSON.stringify(resource.dynamic_attrs);
            clas_project.innerHTML = resource.project;

        };

        var _getPKsFromList = function (list) {
            var invisible = Utk.ArrayUtils.diffArray(list.items, list.visibleItems);
            var res = [];
            for (var i in invisible) {
                res.push(invisible[i]._additionalValues.pk);
            }
            return res;
        };

        var _colListUpdated = function (list) {
            var query = $("#collections-list .search").val();
            MAP._filters.collections[self.properties.pk] = {
                list: _getPKsFromList(list),
                query: query
            };
        };

        var _resListUpdated = function (list) {
            var query = $("#resources-list .search").val();
            MAP._filters.resources[self.properties.pk] = {
                list: _getPKsFromList(list),
                query: query
            };
        };

        var _clasListUpdated = function (list) {
            var query = $("#resources-list .search").val();
            MAP._filters.classifications[self.properties.pk] = {
                list: _getPKsFromList(list),
                query: query
            };

            var _list = [];
            for (var i in list.visibleItems) {
                _list.push(list.visibleItems[i]._additionalValues.pk);
            }
            MAP._specFilters = _list;
        };

        var getLocationData = function (marker, sType, builder, lister) {
            _clearActive();
            var url = "";
            var message = "";
            var options = {};
            switch (sType) {
                case "resources":
                    L.DomUtil.addClass(resTab, 'active');
                    message = L._("loading resources");
                    url = '/storage/api/resources_map.json?locations_map=';
                    options = {
                        valueNames: [
                            's-name',
                            's-tags',
                            's-desc',
                            's-deployment'
                        ]
                    };
                    break;
                case "collections":
                    L.DomUtil.addClass(colTab, 'active');
                    message = L._("loading collections");
                    url =
                        '/storage/api/collections_map.json?locations_map=';
                    options = {
                        valueNames: [
                            's-name'
                        ]
                    };
                    break;
                case "classifications":
                    L.DomUtil.addClass(clasTab, 'active');
                    message = L._("loading classifications");
                    url =
                        '/media_classification/api/classifications_map.json?status=True&locations_map=';
                    options = {
                        valueNames: [
                            's-name',
                            's-tags',
                            's-desc',
                            's-stat_attrs',
                            's-dyna_attrs',
                            's-clas_project',
                            's-deployment'
                        ]
                    };
                    break;
            }

            innerContainer.innerHTML = "<p class=\"gm-info\">" + message + "</p>";
            url = url + marker.properties.pk;
            var id = Math.random();
            MAP.fire('dataloading', {
                id: id
            });
            $.ajax({
                url: url,
                async: true,
                dataType: 'json',
                success: function (data) {
                    MAP.fire('dataload', {
                        id: id
                    });
                    if (data.length > 0) {
                        innerContainer.innerHTML =
                            "";
                    } else {
                        innerContainer.innerHTML =
                            "<p class=\"gm-info\">no items found</p>";
                        return;
                    }
                    if (sType === 'classifications') {
                        _buildClassificationSelect(innerContainer, classification_projects);
                    }
                    var sContainer = L.DomUtil.create(
                        'div', '',
                        innerContainer);
                    sContainer.id =
                        sType + '-list';

                    if (data.length > 0) {
                        _buildFilter(sContainer);
                    }
                    var ul = L.DomUtil.create('ul',
                        'list', sContainer);
                    for (var i in data) {
                        builder(data[i], ul);
                    }
                    var resList = new List(
                        sType + '-list',
                        options);
                    for (var j in resList.items) {
                        resList.items[j]._additionalValues = data[j];
                    }
                    if (MAP._filters[sType] && MAP._filters[sType][marker.properties.pk]) {
                        $("#" + sType + "-list .search").val(
                            MAP._filters[sType][marker.properties.pk].query
                        );
                        resList.search(
                            MAP._filters[sType][marker.properties.pk].query);
                    }
                    if (sType === 'classifications') {
                        $("#select-clas-project-loc").change(function () {
                            var current_clas_project = null;
                            var checked = $("#my-classifications-cb").prop('checked');
                            if ($(this).val() !== '') {
                                current_clas_project = $(this).val();
                            }
                            if (current_clas_project) {
                                if (!checked) {
                                    resList.filter(function (item) {
                                        if (item.values()['s-clas_project'] == current_clas_project) {
                                            return true;
                                        }
                                    });
                                } else {
                                    resList.filter(function (item) {
                                        if (item.values()['s-clas_project'] == current_clas_project &&
                                            item.values()['s-classification'] == current_clas_project) {
                                            return true;
                                        }
                                    });
                                }
                            } else {
                                if (!checked) {
                                    resList.filter();
                                } else {
                                    resList.filter(function (item) {
                                        if (item.values()['s-classification']) {
                                            return true;
                                        }
                                    });
                                }
                            }
                            return false;
                        });
                        $("#my-classifications-cb").change(function () {
                            var checked = $(this).prop('checked');
                            var current_clas_project = null;
                            if ($('#select-clas-project-loc').val() !== '') {
                                current_clas_project = $('#select-clas-project-loc').val();
                            }
                            if (current_clas_project) {
                                if (!checked) {
                                    resList.filter(function (item) {
                                        if (item.values()['s-clas_project'] === current_clas_project) {
                                            return true;
                                        }
                                    });
                                } else {
                                    resList.filter(function (item) {
                                        if (item.values()['s-clas_project'] === current_clas_project &&
                                            item.values()['s-classification'] == current_clas_project) {
                                            return true;
                                        }
                                    });
                                }
                            } else {
                                if (!checked) {
                                    resList.filter();
                                } else {
                                    resList.filter(function (item) {
                                        if (item.values()['s-classification']) {
                                            return true;
                                        }
                                    });
                                }
                            }
                            return false;
                        });

                    }

                    resList.on('updated', lister);
                },
                error: function (data) {
                    MAP.fire('dataload', {
                        id: id
                    });
                    innerContainer.innerHTML =
                        "Error";
                }
            });
        };

        L.DomEvent
            .addListener(resBtn, 'click', L.DomEvent.stop)
            .addListener(resBtn, 'click',
            function () {
                getLocationData(this, 'resources',
                    _buildResource, _resListUpdated);
            }, this);
        L.DomEvent
            .addListener(colBtn, 'click', L.DomEvent.stop)
            .addListener(colBtn, 'click',
            function () {
                getLocationData(this, 'collections',
                    _buildCollection, _colListUpdated);
            }, this);
        L.DomEvent
            .addListener(clasBtn, 'click', L.DomEvent.stop)
            .addListener(clasBtn, 'click',
            function () {
                getLocationData(this, 'classifications',
                    _buildClassification, _clasListUpdated);
            }, this);

        this.markerDetailsPanel = container;

        return container;
    },

});


var clearMovingMarker = function() {
    if (MAP.createMarkerTrapperControl.create_marker) {
        MAP.removeLayer(MAP.createMarkerTrapperControl.create_marker);
        MAP.createMarkerTrapperControl.create_marker = null;
    }
    MAP.off('click', Trapper.Geomap._mapClicked);
};


Trapper.Geomap.ModifyTrapperMarkerControl = function () {

    this.openMarkerUI = function (options) {
        var self = this;
        this.BuildModifyTrapperMarkerContainer(options);
        var ui = L.Storage.fire("ui:start", {
            data: {
                html: this.ModifyTrapperMarkerContainer
            }
        });
        ui.once("ui:end", clearMovingMarker);
    };

    this.BuildModifyTrapperMarkerContainer = function (options) {
        var container = L.DomUtil.create('div', 'modify-location'),
            title = L.DomUtil.create('h4', '', container),
            filterform = L.DomUtil.create('div',
                'modify-location-form-div', container),
            updateButton = L.DomUtil.create('input', '', container),
            map = this._map;
        filterform.id = "filter_form_container_id";

        title.innerHTML = L._('Update location');
        updateButton.type = "button";
        updateButton.value = L._('Update');
        updateButton.className = "button";
        var id = Math.random();
        MAP.fire('dataloading', {
            id: id
        });
        $.ajax({
            url: '/geomap/location/' + options.location_id +
            '/editform/',
            success: function (json) {
                if (json) {
                    filterform.innerHTML = json.location_form_html;
                    options.marker.innerHTML = json.location_form_html;
                    $('#id_latitude')
                        .change(function (e) {
                            var lat = $(this)
                                .val();
                            var lng = $(
                                '#id_longitude')
                                .val();
                            options.marker._moveMarker(
                                lat, lng);
                        });
                    $('#id_longitude')
                        .change(function (e) {
                            var lat = $('#id_latitude')
                                .val();
                            var lng = $(this)
                                .val();
                            options.marker._moveMarker(
                                lat, lng);
                        });
                }
            },
            error: function (data) {
                L.S.fire("ui:end", {});
                L.S.fire('ui:alert', {
                    content: data.responseText,
                    level: 'error'
                });
            },
            complete: function (data) {
                MAP.fire('dataload', {
                    id: id
                });
            }
        });

        var updateMarker = function () {
            var data = $(".modify-location-form-div :input")
                .serialize();
            var id = Math.random();
            MAP.fire('dataloading', {
                id: id
            });
            $.ajax({
                url: '/geomap/location/' + options.location_id +
                '/editform/',
                data: data,
                type: 'POST',
                success: function (json) {
                    if (json && json.success) {
                        L.S.fire('ui:alert', {
                            content: L._(
                                'You have successfully updated selected location.'
                            ),
                            level: 'info'
                        });
                        clearMovingMarker();
                        MAP.off('click', Trapper.Geomap._mapClicked);
                        L.S.fire("ui:end", {});
                        MAP.primary_layer.fetchRemoteData();
                    } else if (json && json.location_form_html) {
                        filterform.innerHTML = json.location_form_html;
                    }
                    MAP.fire('dataload', {
                        id: id
                    });
                },
                error: function (data) {
                    L.S.fire("ui:end", {});
                    L.S.fire('ui:alert', {
                        content: data.responseText,
                        level: 'error'
                    });
                },
                complete: function (data) {
                    MAP.fire('dataload', {
                        id: id
                    });
                }
            });

        };

        L.DomEvent
            .addListener(updateButton, 'click', L.DomEvent.stop)
            .addListener(updateButton, 'click',
            updateMarker, this);

        this.ModifyTrapperMarkerContainer = container;
    };
};

Trapper.Geomap.CreateTrapperMarkerControl = function () {

    var self = this;

    this.openMarkerUI = function (options) {
        var self = this;
        this.BuildCreateTrapperMarkerContainer(options);
        L.Storage.fire("ui:start", {
            data: {
                html: this.ModifyTrapperMarkerContainer
            }
        });
    };
    this.marker_options = {};
    this._latLngToWKT = function (latLng) {
        return "POINT (" + latLng.lng + " " + latLng.lat + ")";
    };

    this.updateMarker = function () {
        var lat = $("#id_latitude")
            .val();
        var lng = $("#id_longitude")
            .val();
        if (lat !== "" && lng !== "") {
            var latlng = L.latLng(lat, lng);
            if (self.create_marker) {
                self.create_marker.setLatLng(latlng);
            } else {
                self.create_marker = L.marker(latlng, {
                    draggable: 'true'
                });
                self.create_marker.addTo(self.map);
                self.create_marker.on('dragend', function (event) {
                    var marker = event.target;
                    var position = marker.getLatLng();
                    self.updateForm(position);
                });
            }
            $("#id_coordinates")
                .val(self._latLngToWKT(latlng));
            self.map.panTo(latlng);
        }
    };

    this.updateForm = function (latLng) {
        /*
         Updates form with selected value. Normalize longitude
         if outside of <-180, 180>
         */
        var lat = latLng.lat;
        var lng = latLng.lng;
        if (lng > 180) {
            lng = lng - 360;
        } else if (lng < -180) {
            lng = lng + 360;
        }
        $("#id_latitude")
            .val(lat);
        $("#id_longitude")
            .val(lng);
        latLng = L.latLng(lat, lng);
        $("#id_coordinates")
            .val(this._latLngToWKT(latLng));
    };

    this.BuildCreateTrapperMarkerContainer = function (options) {
        var container = L.DomUtil.create('div', 'create-location'),
            title = L.DomUtil.create('h4', '', container),
            filterform = L.DomUtil.create('div',
                'create-location-form-div', container),
            createButton = L.DomUtil.create('input', '', container),
            map = this._map;
        self = this;
        this.map = MAP;
        filterform.id = "filter_form_container_id";

        title.innerHTML = L._('Create location');
        createButton.type = "button";
        createButton.value = L._('Create');
        createButton.className = "button";
        var id = Math.random();
        MAP.fire('dataloading', {
            id: id
        });
        $.ajax({
            url: '/geomap/location/createform/',
            success: function (json) {
                if (json) {
                    filterform.innerHTML = json.location_form_html;
                    $('#id_latitude')
                        .change(self.updateMarker);
                    $('#id_longitude')
                        .change(self.updateMarker);
                }
            },
            error: function (data) {
                L.S.fire("ui:end", {});
                L.S.fire('ui:alert', {
                    content: data.responseText,
                    level: 'error'
                });
            },
            complete: function (data) {
                MAP.fire('dataload', {
                    id: id
                });
            }
        });

        var createMarker = function () {
            var data = $(".create-location-form-div :input")
                .serialize();
            var id = Math.random();
            MAP.fire('dataloading', {
                id: id
            });
            $.ajax({
                url: '/geomap/location/createform/',
                data: data,
                type: 'POST',
                success: function (json) {
                    if (json && json.success) {
                        L.S.fire('ui:alert', {
                            content: L._(
                                'Marker created'
                            ),
                            level: 'info'
                        });
                        if (json && json.id) {
                            MAP.primary_layer.options.remoteData.url = 
                                MAP._base_trapper_url + "&locations_map=" + json.id;
                            document._mapParameters.pk = json.id.toString();
                            MAP.off('click', Trapper.Geomap._mapClicked);
                            MAP.primary_layer.fetchRemoteData();
                            MAP.removeLayer(self.create_marker);
                            L.S.fire("ui:end", {});
                        }
                    } else if (json && json.location_form_html) {
                        filterform.innerHTML = json.location_form_html;
                        $('#id_latitude')
                            .change(self.updateMarker);
                        $('#id_longitude')
                            .change(self.updateMarker);
                    }
                    MAP.fire('dataload', {
                        id: id
                    });
                },
                error: function (data) {
                    L.S.fire("ui:end", {});
                    L.S.fire('ui:alert', {
                        content: data.responseText,
                        level: 'error'
                    });
                    MAP.removeLayer(self.create_marker);
                    MAP.off('click', Trapper.Geomap._mapClicked);
                },
                complete: function (data) {
                    MAP.fire('dataload', {
                        id: id
                    });
                }
            });
        };

        L.DomEvent
            .addListener(createButton, 'click', L.DomEvent.stop)
            .addListener(createButton, 'click',
            createMarker, this);

        this.ModifyTrapperMarkerContainer = container;
    };
};

Trapper.Geomap._mapClicked = function (e) {
    var latLng = e.latlng;
    e.target.createMarkerTrapperControl.updateForm(latLng);
    if (e.target.createMarkerTrapperControl.create_marker) {
        e.target.createMarkerTrapperControl.create_marker.setLatLng(latLng);
    } else {
        e.target.createMarkerTrapperControl.create_marker = L.marker(latLng, {
            draggable: 'true'
        });
        e.target.createMarkerTrapperControl.create_marker.addTo(e.target);
        e.target.createMarkerTrapperControl.create_marker.on('dragend', function (event) {
            var marker = event.target;
            var position = marker.getLatLng();
            e.target.createMarkerTrapperControl.updateForm(position);
        });
    }
};
