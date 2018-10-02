'use strict';

(function (global, namespace, moduleName) {

    var module = {};

    var plugins = global[namespace].Plugins;
    var alert = global[namespace].Alert;
    var modal = global[namespace].Modal;
    var uploader = global[namespace].Uploader;

    var doc = global.document;

    module.init = function () {
        console.log(moduleName + ' initialize');
    };

    module.upload = function () {
        plugins.fileInputs();
        plugins.select2();
    };

// if passed namespace does not exist, create one
    global[namespace] = global[namespace] || {};

// append module to given namespace
    global[namespace][moduleName] = module;

}(window, 'TrapperApp', 'Location'));
