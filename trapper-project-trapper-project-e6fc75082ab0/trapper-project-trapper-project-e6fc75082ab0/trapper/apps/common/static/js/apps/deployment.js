'use strict';

(function(global, namespace, moduleName) {

    var module = {};

    var plugins = global[namespace].Plugins;
    var alert = global[namespace].Alert;
    var modal = global[namespace].Modal;

    var doc = global.document;

    module.init = function() {
	console.log(moduleName + ' initialize');
    };

    var deleteConfirm = function () {
        var deleteBtn = doc.querySelector('.btn-delete');
        
        if (!deleteBtn) {
            return;
        }

        deleteBtn.addEventListener('click', showModal);

        function showModal(e) {
            e.preventDefault();

            modal.confirm({
                title: 'Delete deployment',
                content: 'Are you sure you want to delete this deployment?',
                buttons: [{
                    type: 'success',
                    label: 'Yes',
                    onClick: function () {
                        window.location = e.target.href;
                    }
                }, {
                    type: 'danger',
                    label: 'No'
                }]
            });
        }
    };

    module.create = module.update = function() {
	plugins.select2();
	plugins.map();
	plugins.datepicker();
    };

    module.upload = function () {
        plugins.fileInputs();
        plugins.select2();
    };

    module.preview = function () {
        deleteConfirm();
        plugins.smallMap();
    };

    // if passed namespace does not exist, create one
    global[namespace] = global[namespace] || {};
    
    // append module to given namespace
    global[namespace][moduleName] = module;
    
}(window, 'TrapperApp', 'Deployment'));
