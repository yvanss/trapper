'use strict';

(function (global, namespace, moduleName) {

    var module = {};

    var plugins = global[namespace].Plugins;
    var alert = global[namespace].Alert;
    var modal = global[namespace].Modal;
    var uploader = global[namespace].Uploader;

    var doc = global.document;

    var deleteConfirm = function () {
        var deleteBtns = doc.querySelectorAll('.btn-delete');        
        [].forEach.call(deleteBtns, function (btn) {
            btn.addEventListener('click', showModal);
            
            function showModal(e) {
                e.preventDefault();
                
                modal.confirm({
                    title: 'Delete data package',
                    content: 'Are you sure you want to delete this data package?',
                    buttons: [{
                        type: 'success',
                        label: 'Yes',
                        onClick: function () {
                            window.location = e.target.parentNode.href;
                        }
                    }, {
                        type: 'danger',
                        label: 'No'
                    }]
                });
            };
        })
    };        
    
    var celery = function () {
        function getInfo(btn) {
            var td = btn.parentNode.parentNode.querySelectorAll('td');

            return 'Name: ' + td[0].innerHTML;
        }

        var cancelBtns = doc.querySelectorAll('.btn-cancel'),
            logBtns = doc.querySelectorAll('.btn-log');

        [].forEach.call(cancelBtns, function (btn) {
            btn.addEventListener('click', function (event) {
                event.preventDefault();

                var target = event.target;

                if (target.tagName.toLowerCase() === 'span') {
                    target = target.parentNode;
                }

                modal.confirm({
                    title: 'Do you want to cancel the celery task?',
                    content: getInfo(btn),
                    buttons: [{
                        type: 'danger',
                        label: 'Yes',
                        onClick: function () {
                            send(target.href, target.dataset['task']);
                        }
                    }, {
                        type: 'default',
                        label: 'Cancel'
                    }]
                });
            });
        });

        [].forEach.call(logBtns, function (btn) {
            btn.addEventListener('click', function (event) {
                event.preventDefault();

                var target = event.target;

                if (target.tagName.toLowerCase() === 'span') {
                    target = target.parentNode;
                }

                var content = target.parentNode.querySelector('div[data-title]');

                var opts = getOptions(content.dataset.mode);

                modal.alert({
                    title: opts.icon + ' ' + content.dataset.title,
                    content: content.innerHTML,
                    mode: opts.className
                });
            });
        });

        function getOptions(mode) {
            var modes = {
                started: {
                    className: 'text-primary',
                    icon: '<span class="fa fa-spin fa-refresh"></span>'
                },
                success: {
                    className: 'text-success',
                    icon: '<span class="fa fa-check"></span>'
                },
                retry: {
                    className: 'text-warning',
                    icon: '<span class="fa fa-exclamation"></span>'
                },
                failure: {
                    className: 'text-danger',
                    icon: '<span class="fa fa-close"></span>'
                },
                default: {
                    className: '',
                    icon: ''
                }
            };

            if (!modes.hasOwnProperty(mode)) {
                mode = 'default';
            }

            return modes[mode];
        }

        function c(k) {
            return (doc.cookie.match('(^|; )' + k + '=([^;]*)') || 0)[2];
        }

        function send(url, taskId) {
            var sender = doc.createElement('form'),
            input = doc.createElement('input'),
            csrf = doc.createElement('input');
            
            sender.method = 'POST';
            sender.action = url;

            input.type = 'hidden',
            input.name = 'task_id';
            input.value = taskId;
            
            csrf.type = 'hidden';
            csrf.name = 'csrfmiddlewaretoken';
            csrf.value = c('csrftoken');

            sender.appendChild(csrf);
            sender.appendChild(input);
            
            doc.body.appendChild(sender);
            
            sender.submit();
        }
    };

    module.init = function () {
        console.log(moduleName + ' initialize');
        celery();
        deleteConfirm();
    };

// if passed namespace does not exist, create one
    global[namespace] = global[namespace] || {};

// append module to given namespace
    global[namespace][moduleName] = module;

}(window, 'TrapperApp', 'Dashboard'));
