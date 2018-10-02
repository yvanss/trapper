'use strict';

(function (global, namespace, moduleName) {

    var module = {};

    var plugins = global[namespace].Plugins;
    var alert = global[namespace].Alert;
    var modal = global[namespace].Modal;
    var uploader = global[namespace].Uploader;

    var doc = global.document;

    var attrsOrderer = function (id) {
        var table = doc.getElementById(id),
            field = doc.getElementById(id + '_order');

        function setOrder() {
            var nameCells = table.querySelectorAll('tr > td:first-child');

            field.value = [].map.call(nameCells, function (cell) {
                return cell.textContent;
            }).join(',');
        }

        function changeRows(row, offset) {
            var allRows = table.querySelectorAll('tr');
            if (row.rowIndex === allRows.length - 1 && offset > 0) {
                return;
            }
            if (row.rowIndex === 1 && offset < 0) {
                return;
            }

            var rowToReplace = allRows[row.rowIndex + offset];

            if (offset > 0) {
                row.parentNode.insertBefore(rowToReplace, row);
            } else {
                row.parentNode.insertBefore(row, rowToReplace);
            }
        }

        table.addEventListener('click', function (event) {
            var target = event.target;
            var move = 0;
            if (target.tagName === 'SPAN') {
                target = target.parentNode;
            }

            move = parseInt(target.dataset.move, 10);
            if (move) {
                changeRows(target.parentNode.parentNode, move);
                setOrder();
            }
        });
    };

    var clearCustomForm = function () {
        var btn = doc.querySelector('[data-clear]');
        var clearable = btn.parentNode.querySelectorAll('input, select, textarea');

        function clearFields() {
            [].forEach.call(clearable, function (field) {
                if (field.type === 'text' || field.type === 'textarea' || field.type === 'hidden') {
                    field.value = '';
                } else if (field.type === 'checkbox') {
                    field.checked = false;
                } else {
                    if (field.classList.contains('select2-default')) {
                        $(field).select2('val', field.options[0].value);
                    } else {
                        [].forEach.call(field.options, function (option) {
                            option.selected = false;
                        });
                    }
                }
            });
        }

        btn.addEventListener('click', function (event) {
            event.preventDefault();

            clearFields();
        });
    };

    var customFormObserver = function () {
        var type = doc.getElementById('id_field_type'),
            values = doc.getElementById('id_values');

        var valCache = '';

        type.addEventListener('change', function () {
            if (type.value === 'Boolean') {
                valCache = values.value;
                values.value = '';
                values.disabled = true;
            } else {
                values.value = valCache;
                values.disabled = false;
            }
        });
    };

    module.init = function () {
        console.log(moduleName + ' initialize');
    };

    module.edit = module.update = module.create = function () {
        attrsOrderer('id_static_attrs');
        attrsOrderer('id_dynamic_attrs');

        customFormObserver();

        plugins.collapsable();

        clearCustomForm();

        plugins.select2();
    };

// if passed namespace does not exist, create one
    global[namespace] = global[namespace] || {};

// append module to given namespace
    global[namespace][moduleName] = module;

}(window, 'TrapperApp', 'Classificator'));