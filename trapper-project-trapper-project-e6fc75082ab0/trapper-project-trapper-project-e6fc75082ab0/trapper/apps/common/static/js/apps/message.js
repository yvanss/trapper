'use strict';

(function (global, namespace, moduleName) {

    var module = {};

    var plugins = global[namespace].Plugins;
    var alert = global[namespace].Alert;
    var modal = global[namespace].Modal;
    var uploader = global[namespace].Uploader;

    var doc = global.document;

    var pagination = function () {
        var id = 'page';
        var input = doc.querySelector('#' + id);

        if (!input) {
            return;
        }

        var count = parseInt(doc.querySelector('label[for="' + id + '"]').innerHTML.split(' ')[1], 10);
        var active = input.value;

        function changePage() {
            var page = parseInt(input.value, 10);

            if (page > 0 && page <= count) {
                active = page;
                global.location.search = 'page=' + page;
            } else {
                input.value = active;
            }
        }

        input.addEventListener('keyup', changePage);
        input.addEventListener('change', changePage);
    };

    var requests = function () {
        var buttons = doc.querySelectorAll('button[data-resolve], button[data-revoke]');

        if (!buttons.length) {
            return;
        }

        function chooseAction(event) {
            var resolve = !!event.target.dataset.resolve;
            var type = event.target.dataset.type;

            if (resolve) {
                var content = 'How would you like to resolve this request?',
                title = 'Collection request: resolve',
                labelYes = 'Accept',
                labelNo = 'Reject';
            } else {
                var content = 'Are you sure?',
                title = 'Collection request: revoke',
                labelYes = 'Yes',
                labelNo = 'No';
            }

            modal.confirm({
                title: title,
                content: content,
                buttons: [{
                    type: 'success',
                    label: labelYes,
                    onClick: function () {
                        var url = resolve ? event.target.dataset.resolve : event.target.dataset.revoke;
                        send(url, true);
                    }
                }, {
                    type: 'danger',
                    label: labelNo,
                    onClick: function () {
                        if (resolve) {
                            send(event.target.dataset.resolve, false);
                        }
                    }
                }]
            });
        }

        function c(k) {
            return (doc.cookie.match('(^|; )' + k + '=([^;]*)') || 0)[2];
        }

        function send(url, decision) {
            var sender = doc.createElement('form'),
                input = doc.createElement('input'),
                csrf = doc.createElement('input');

            sender.method = 'POST';
            sender.action = url;

            input.type = 'hidden';
            input.name = (decision ? 'yes' : 'no');
            input.value = 'true';

            csrf.type = 'hidden';
            csrf.name = 'csrfmiddlewaretoken';
            csrf.value = c('csrftoken');

            sender.appendChild(input);
            sender.appendChild(csrf);

            doc.body.appendChild(sender);

            sender.submit();
        }

        [].forEach.call(buttons, function (button) {
            button.addEventListener('click', chooseAction);
        });
    };

    module.new = function () {
        plugins.select2();
        plugins.wysiwyg();
    };

    module.list = function () {
        pagination();

        requests();
    };

    module.preview = function () {
        requests();
    };

// if passed namespace does not exist, create one
    global[namespace] = global[namespace] || {};

// append module to given namespace
    global[namespace][moduleName] = module;

}(window, 'TrapperApp', 'Message'));
