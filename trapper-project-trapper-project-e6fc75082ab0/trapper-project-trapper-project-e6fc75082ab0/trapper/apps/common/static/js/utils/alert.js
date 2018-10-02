'use strict';

(function (global, namespace, moduleName) {

    var module = {};

    var doc = global.document;

    var options = {
        delay: 7500
    };

    var containerId = 'alerts',
        container;

    var icons = {
        info: 'info',
        success: 'check',
        danger: 'times',
        warning: 'exclamation'
    };

    var createAlert = function (message, mode) {
        mode = mode || 'info';

        var alert = doc.createElement('div');
        alert.className = 'alert alert-' + mode;
        alert.innerHTML = '<div style="width:100%">' + message +
        ' <button type="button" class="alert-close"></button></div>';

        return alert;
    };

// get alerts' container DOM object if exists or create one
    var getContainer = function () {
        var container = doc.getElementById(containerId);

        if (!container) {
            container = doc.createElement('div');
            container.id = containerId;
            container.className = 'alerts-global';

            doc.body.appendChild(container);
        }

        return container;
    };

    var showAlert = function (alert, delay) {
        container.appendChild(alert);

        setTimeout(function () {
            alert.classList.add('active');
        }, 50);

        setTimeout(function () {
            hideAlert(alert);
        }, delay);
    };

    var hideAlert = function (alert) {
        if (!alert) {
            return;
        }

        alert.classList.remove('active');

        setTimeout(function () {
            container.removeChild(alert);
        }, 300);
    };

    module.init = function () {
        container = getContainer();

        container.addEventListener('click', function (e) {
            e.preventDefault();

            if (e.target.classList.contains('alert-close')) {
                hideAlert(e.target.parentNode.parentNode);
            }
        });

        // fetch all the alerts passed with HTML template
        var alerts = container.querySelectorAll('.alert');
        container.innerHTML = '';

        [].forEach.call(alerts, function (alert) {
            showAlert(alert, options.delay);
        });
    };

    module.addMessage = function (message, mode, delay) {
        delay = delay || options.delay;

        var alert = createAlert(message, mode);

        showAlert(alert, delay);
    };

    module.info = function (message, delay) {
        module.addMessage(message, 'info', delay);
    };

    module.success = function (message, delay) {
        module.addMessage(message, 'success', delay);
    };

    module.warning = function (message, delay) {
        module.addMessage(message, 'warning', delay);
    };

    module.error = function (message, delay) {
        module.addMessage(message, 'danger', delay);
    };


// if passed namespace does not exist, create one
    global[namespace] = global[namespace] || {};

// append module to given namespace
    global[namespace][moduleName] = module;

}(window, 'TrapperApp', 'Alert'));
