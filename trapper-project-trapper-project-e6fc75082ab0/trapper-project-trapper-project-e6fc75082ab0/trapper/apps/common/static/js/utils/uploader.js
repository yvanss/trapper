'use strict';

(function (global, namespace, moduleName) {

    var module = {};

// if passed namespace does not exist, create one
    global[namespace] = global[namespace] || {};

// append module to given namespace
    global[namespace][moduleName] = module;

}(window, 'TrapperApp', 'Uploader'));