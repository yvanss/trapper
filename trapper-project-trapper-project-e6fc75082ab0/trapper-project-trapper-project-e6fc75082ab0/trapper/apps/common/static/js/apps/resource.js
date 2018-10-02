'use strict';

(function (global, namespace, moduleName) {

    var module = {};

    var plugins = global[namespace].Plugins;
    var alert = global[namespace].Alert;
    var modal = global[namespace].Modal;
    var uploader = global[namespace].Uploader;

    var doc = global.document;

    var comments = function () {
        var replyBtns = doc.querySelectorAll('.btn-reply');
        var parentId = doc.querySelector('#id_parent');
        var message = doc.querySelector('#id_comment');

        function reply(event) {
            parentId.value = event.target.parentNode.parentNode.parentNode.dataset.pk;
            message.focus();
        }

        [].forEach.call(replyBtns, function (btn) {
            btn.addEventListener('click', reply);
        });
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
                title: 'Delete resource',
                content: 'Are you sure you want to delete this resource?',
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

    var media = function () {
        var medias = doc.querySelectorAll('[data-media]');

        if (!medias.length) {
            return;
        }

        [].forEach.call(medias, function (media) {
            media.addEventListener('click', function (event) {
                event.preventDefault();

                modal[media.dataset.media](media.href);
            });
        });
    };

    module.list = function () {
        console.log(moduleName + ' initialize');
        plugins.select2();
    };

    module.upload = module.update = function () {
        plugins.select2();
        plugins.fileInputs();
        plugins.datepicker();
    };

    module.request = function () {
        plugins.wysiwyg();
    };

    module.preview = function () {
        deleteConfirm();
        comments();
        plugins.smallMap();
        media();
    };

// if passed namespace does not exist, create one
    global[namespace] = global[namespace] || {};

// append module to given namespace
    global[namespace][moduleName] = module;

}(window, 'TrapperApp', 'Resource'));
