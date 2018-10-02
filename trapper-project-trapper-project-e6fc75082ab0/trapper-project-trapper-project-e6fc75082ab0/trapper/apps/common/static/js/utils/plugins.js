window.L = window.L || {};

(function (global, namespace, moduleName, $, L) {
    'use strict';

    var doc = global.document;

    var module = {
        tooltip: function () {
            $('[data-tooltip=tooltip]').tooltip();
        },

        enableToggler: function (container) {
            var checkboxes = container.querySelectorAll('input[type="checkbox"]');

            [].forEach.call(checkboxes, function (checkbox) {
                var field = checkbox.parentNode.querySelector('select');

                checkbox.addEventListener('change', function (e) {
                    field.disabled = !e.target.checked;
                });
            });
        },

        collapsable: function () {
            function preprocess(trigger) {
                var id = 'collapsable-' + (counter++);
                var target = trigger.nextSibling;
                var isActive = trigger.classList.contains('active');

                while (target.nodeType !== 1) {
                    target = target.nextSibling;
                }
                trigger.dataset.target = '#' + id;
                trigger.dataset.toggle = 'collapse';
                if (!isActive) {
                    trigger.classList.add('collapsed');
                }

                var wrapper = doc.createElement('div');
                wrapper.id = id;
                wrapper.className = 'collapse' + (isActive ? ' in' : '');
                wrapper.appendChild(target.cloneNode(true));

                trigger.parentNode.replaceChild(wrapper, target);
            }

            var counter = 0;
            var collapsable = doc.querySelectorAll('.collapsable');

            if (!collapsable.length) {
                return;
            }

            [].forEach.call(collapsable, preprocess);
        },

        annotations: function (box) {
            var inputFrom, inputTo;
            var btnSet, btnGet, btnPlay;

            var inputs = box.querySelectorAll('input');

            inputFrom = inputs[0];
            inputTo = inputs[1];

            btnSet = box.querySelector('.btn-set');
            btnGet = box.querySelector('.btn-get');
            btnPlay = box.querySelector('.btn-play');

            if (btnGet) {
                btnGet.addEventListener('click', function (e) {
                    e.preventDefault();

                    var time = videoPlayer.getValueSlider();

                    inputFrom.value = secondsToTime(time.start);
                    inputTo.value = secondsToTime(time.end);
                });
            }

            if (btnSet) {
                btnSet.addEventListener('click', function (e) {
                    e.preventDefault();

                    var start = timeToSeconds(inputFrom.value);
                    var end = timeToSeconds(inputTo.value);

                    videoPlayer.setValueSlider(start, end);
                });
            }

            if (btnPlay) {
                btnPlay.addEventListener('click', function (e) {
                    e.preventDefault();

                    videoPlayer.play();

                    setTimeout(function () {
                        var start = timeToSeconds(inputFrom.value);
                        var end = timeToSeconds(inputTo.value);

                        videoPlayer.loopBetween(start, end);
                    });
                });
            }
        },

        repeatbleTable: function (table, cb) {
            var namePrefix = table.dataset.name;
            var tbody = table.querySelector('tbody');
            var template = tbody.querySelector('tr:last-child').innerHTML;

            var reg = new RegExp('(' + namePrefix + '-)(\\d)', 'g');

            var totalInput = doc.querySelector('input[name=' + namePrefix + '-TOTAL_FORMS]'),
                filledInput = doc.querySelector('input[name=' + namePrefix + '-INITIAL_FORMS]'),
                maxInput = doc.querySelector('input[name=' + namePrefix + '-MAX_NUM_FORMS]');

            var filled = parseInt(filledInput.value, 10),
                max = parseInt(maxInput.value, 10),
                total = parseInt(totalInput.value, 10);

            var index = total;

            tbody.addEventListener('click', function (event) {
                var target = event.target;

                if (target.tagName.toLowerCase() === 'span') {
                    target = target.parentNode;
                }

                if (target.tagName.toLowerCase() === 'button' && target) {

                    if (target.classList.contains('btn-add-row')) {
                        addRow(target);
                    } else if (target.classList.contains('btn-remove-row')) {
                        removeRow(target);
                    }
                }
            });

            function createRow() {
                var row = doc.createElement('tr');

                row.innerHTML = template.replace(reg, '$1' + index);

                return row;
            }

            function updateInputs() {
                totalInput.value = total;
            }

            function addRow(target) {
                if (filled >= max) {
                    return;
                }

                target.parentNode.innerHTML = '<button type="button" class="btn btn-danger btn-remove-row"><span class="fa fa-remove"></span></button>';

                var row = createRow();
                tbody.appendChild(row);
                module.select2();
                if (cb) {
                    cb();
                }

                var ann = row.querySelector('.form-annotation');
                if (ann) {
                    annotations(ann);
                }

                index++;
                total++;
                updateInputs();
            }

            function removeRow(target) {
                var row = target.parentNode.parentNode;
                var checkbox = row.querySelector('td:last-child input[type=checkbox]');

                if (checkbox) {
                    checkbox.checked = true;
                    row.style.display = 'none';
                } else {
                    row.remove();
                    total--;
                    updateInputs();
                }
            }
        },

        fileInputs: function () {
            function helper(input) {
                var fakeInput = input.parentElement.querySelector('input[type=text]');

                input.addEventListener('change', function (e) {
                    e.preventDefault();

                    var value = '';

                    [].forEach.call(e.target.files, function (file) {
                        value = value + file.name + '; ';
                    });

                    fakeInput.value = value;
                });
            }

            var fileInputs = doc.querySelectorAll('.file-group input[type=file]');

            if (!fileInputs.length) {
                return;
            }

            [].forEach.call(fileInputs, helper);
        },

        datepicker: function () {
            $('.datepicker-control').datepicker({
                format: 'dd.mm.yyyy',
                clearBtn: true,
                autoclose: true,
                orientation: 'top left',
                todayHighlight: true
            });

            $('.timepicker-control').timepicker({
                show2400: true,
                timeFormat: 'H:i'
            });

            $('.datetimepicker-control').datetimepicker({
                format: 'DD.MM.YYYY HH:mm:ss',
                showClear: true
            });
        },

        select2: function (options) {
            options = options || {};

            var defaults = {
                minimumResultsForSearch: 5,
                minimumInputLength: 3,
            };

            var settings = $.extend({}, defaults, options);

            $('.select2-default').select2(settings);

            // tokens
            var $tokens = $('.select2-tags');

            if (!$tokens.length) {
                return;
            }

            $tokens.each(function (index, field) {
                $(field).select2({
                    tags: field.dataset.tags.split(','),
                    minimumResultsForSearch: 5,
                    minimumInputLength: 3
                });
            });
        },

        lockerInputs: function () {
            var lockers = doc.querySelectorAll('.control-locker');

            [].forEach.call(lockers, function (locker) {
                locker.addEventListener('change', function (e) {
                    var control = locker.parentNode.parentNode.querySelector('input.controlled, select.controlled');

                    if (e.target.checked) {
                        control.removeAttribute('disabled');
                    } else {
                        control.setAttribute('disabled', 'disabled');
                    }
                });
            });
        },

        map: function (staticURL) {

            if (!$('#location_map').length) {
                return;
            }

            staticURL = staticURL || document.body.dataset['staticUrl'];

            var unselectedIcon = new L.Icon.Default();
            var selectedIcon = new L.Icon.Default();
            selectedIcon.options.iconUrl = staticURL + 'geomap/img/red-marker.png';

            var osm = L.tileLayer('http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 18,
                attribution: 'Map data © <a href="http://openstreetmap.org">OpenStreetMap</a> contributors'
            });
            var esri = L.tileLayer('http://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
                maxZoom: 18,
                attribution: 'Tiles &copy; Esri &mdash; Source: Esri'
            })

            var markers = L.markerClusterGroup();
            var map = L.map('location_map', {layers: [osm,esri]});
            
            var baseMaps = {
                "OSM": osm,
                "ESRI": esri
            };
            var overlayMaps = {"Locations": markers}

            L.control.layers(baseMaps, overlayMaps).addTo(map);

            $('#id_location').change(function () {
                var val = $(this).val();
                clearSelected();
                markers.eachLayer(function (layer) {
                    if (layer._id === val) {
                        selectMarker(layer);
                    }
                });
                if (!val) {
                    map.fitBounds(markers.getBounds());
                }
            });

            var selectMarker = function (marker) {
                marker.setIcon(selectedIcon);
                marker.setZIndexOffset(1000);
                map.setView(marker.getLatLng(), 16);
            };

            var clearSelected = function () {
                markers.eachLayer(function (layer) {
                    layer.setIcon(unselectedIcon);
                    layer.setZIndexOffset(-1000);
                });
            };

            var markerClicked = function (e) {
                clearSelected();
                selectMarker(e.target);
                $('#id_location').select2('val', e.target._id);
            };

            var currentValue = $('#id_location').val();
            $('#id_location').children('option').each(function () {
                var data = $(this).data();
                if (data.longitude) {
                    var marker = L.marker([data.latitude, data.longitude]);
                    marker.on('click', markerClicked);
                    marker._id = $(this).val();
                    marker.bindLabel(data.locationId);
                    if (marker._id === currentValue) {
                        selectMarker(marker);
                    }
                    markers.addLayer(marker);
                }
            });
            markers.addTo(map);
            if (!currentValue) {
                map.fitBounds(markers.getBounds());
            }
        },

        smallMap: function() {
            var latlng = $('#location_small_map').attr("latlng").split(",")
            var osm = L.tileLayer('http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 18,
                attribution: 'Map data © <a href="http://openstreetmap.org">OpenStreetMap</a> contributors'
            });
            var esri = L.tileLayer('http://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
                maxZoom: 18,
                attribution: 'Tiles &copy; Esri'
            })
            var map = L.map('location_small_map', {layers: [osm,esri]}).setView(latlng, 15);
            L.marker(latlng).addTo(map);
            
            var baseMaps = {
                "OSM": osm,
                "ESRI": esri
            };
            L.control.layers(baseMaps).addTo(map);
        },
        
        wysiwyg: function () {
            $('.textarea-wysiswyg').wysihtml5({
                toolbar: {
                    'fa': true,
                    'font-styles': false,
                    'emphasis': true,
                    'lists': true,
                    'html': true,
                    'link': false,
                    'image': false,
                    'color': false,
                    'blockquote': false
                },
                                customTemplates: {
                    link: function (context) {
                        return '<li>' +
                            '<div class="bootstrap-wysihtml5-insert-link-modal modal" data-wysihtml5-dialog="createLink" style="display: none;" aria-hidden="true">' +
                            '<div class="modal-dialog ">' +
                            '<div class="modal-content">' +
                            '<div class="modal-header">' +
                            '<button type="button" class="close" data-dismiss="modal"><span class="fa fa-remove"></span></button>' +
                            '<h3 class="modal-title">' + context.locale.link.insert + '</h3>' +
                            '</div>' +
                            '<div class="modal-body">' +
                            '<div class="form-group">' +
                            '<input value="http://" class="bootstrap-wysihtml5-insert-link-url form-control" data-wysihtml5-dialog-field="href">' +
                            '</div> ' +
                            '</div>' +
                            '<div class="modal-footer">' +
                            '<a class="btn btn-default" data-dismiss="modal" data-wysihtml5-dialog-action="cancel" href="#">' + context.locale.link.cancel + '</a>' +
                            '<a href="#" class="btn btn-primary" data-dismiss="modal" data-wysihtml5-dialog-action="save">' + context.locale.link.insert + '</a>' +
                            '</div>' +
                            '</div>' +
                            '</div>' +
                            '</div>' +
                            '<a class="btn btn-default" data-wysihtml5-command="createLink" title="' + context.locale.link.insert + '" tabindex="-1" href="javascript:;" unselectable="on">' +
                            '<span class="fa fa-link"></span>' +
                            '</a>' +
                            '</li>';
                    },
                    emphasis: function () {
                        return '<li>' +
                            '<div class="btn-group">' +
                            '<a class="btn btn-default" data-wysihtml5-command="bold" tabindex="-1" href="javascript:;" unselectable="on" title="CTRL+B"><span class="fa fa-bold"></span></a>' +
                            '<a class="btn btn-default" data-wysihtml5-command="italic" tabindex="-1" href="javascript:;" unselectable="on" title="CTRL+I"><span class="fa fa-italic"></span></a>' +
                            '<a class="btn btn-default" data-wysihtml5-command="underline" tabindex="-1" href="javascript:;" unselectable="on" title="CTRL+U"><span class="fa fa-underline"></span></a>' +
                            '</div>' +
                            '</li>';
                    }
                },
                events: {
                    load: function () {
                        $('[data-wysihtml5-command]').tooltip({
                            container: 'body'
                        });
                    },
                    'focus:composer': function () {
                        this.composer.editableArea.classList.add('focused');
                    },
                    'blur:composer': function () {
                        this.composer.editableArea.classList.remove('focused');
                    }
                }
            });
        }
    };

    // if passed namespace does not exist, create one
    global[namespace] = global[namespace] || {};

    // append module to given namespace
    global[namespace][moduleName] = module;

}(window, 'TrapperApp', 'Plugins', jQuery, L));
