'use strict';

(function (global, namespace, moduleName, $) {

    var module = {};

    var doc = global.document;

    var $modal;

    var noop = function () {
    };

    var defaults = {
        animation: 'fade',
        buttons: [],
        content: '',
        onHide: noop,
        onShow: noop,
        size: '',
        title: '',
        mode: ''
    };

    var extend = function (options) {
        for (var op in defaults) {
            options[op] = options[op] || defaults[op];
        }
    };

    /* Button object fields:
     * - type - same as css classes, ie. success, default
     * - label
     * - onClick - event listener for click action
     * - hide  - hide modal when clicked, default 'true'
     */
    var processButtons = function (buttons) {
        var elements = doc.createDocumentFragment();

        buttons.forEach(function (button) {
            var tmp = doc.createElement('button');
            tmp.type = 'button';
            tmp.className = 'btn';
            tmp.innerHTML = button.label || 'button';

            if (!button.hasOwnProperty('hide')) {
                button.hide = true;
            }

            if (button.type) {
                tmp.className += ' btn-' + button.type;
            }

            button.onClick = button.onClick || noop;

            tmp.addEventListener('click', function () {
                button.onClick.call(button, $modal);

                if (button.hide) {
                    module.hideModal();
                }
            });

            elements.appendChild(tmp);
        });

        return elements;
    };

    var createTemplate = function (options) {
        var size = options.size ? 'modal-' + options.size : '';
        var template = doc.createElement('div');

        template.className = 'modal ' + options.animation;
        template.tabIndex = -1;

        template.innerHTML = [
            '<div class="modal-dialog ' + size + '">',
            '<div class="modal-content">',
            '<div class="modal-header">',
            '<button type="button" class="close" data-dismiss="modal">',
            '<span class="fa fa-remove"></span>',
            '</button>',
            '<h3 class="modal-title ' + options.mode + '">',
            options.title,
            '</h3>',
            '</div>',
            '<div class="modal-body">',
            options.content,
            '</div>',
            (options.buttons.length ? '<div class="modal-footer"></div>' : ''),
            '</div>',
            '</div>'
        ].join('\n');

        return template;
    };

    module.showModal = function (template, options) {
        $modal = $(template);

        $modal.on('shown.bs.modal', function () {
            options.onShow($modal);
        });

        $modal.on('hidden.bs.modal', function () {
            options.onHide($modal);
            $modal.remove();
        });

        $modal.modal('show');
    };

    module.hideModal = function () {
        $modal.modal('hide');
    };

    module.show = module.alert = function (options) {
        var template;

        extend(options);
        template = createTemplate(options);

        module.showModal(template, options);
    };

    module.external = function (options) {
        if (!options.url) {
            return;
        }

        $.get(options.url, function (content) {
            options.content = content;

            module.show(options);
        });
    };

    module.prompt = module.confirm = function (options) {
        var template, btnElems;

        extend(options);
        template = createTemplate(options);
        btnElems = processButtons(options.buttons);

        template.querySelector('.modal-footer').appendChild(btnElems);

        module.showModal(template, options);
    };

    module.media = function (options) {

        // transform audio, image, video to A, I, V
        var type = options.type.toUpperCase()[0];

        if (type === 'I') {
            module.image(options.url, options.mime, options.title, options.mime);
        } else if (type === 'A') {
            module.audio(options.url, options.mime, options.title);
        } else if (type === 'V') {
            module.video(options.url, options.mime, options.title);
        }
    };

    var types = {
        'mp4': 'mp4',
        'm4v': 'mp4',
        'webm': 'webm',
        'ogv': 'ogg',
        'wav': 'wav',
        'aac': 'aac',
        'mp3': 'mpeg',
        'mpg': 'mpeg',
        'mpeg': 'mpeg',
        'oga': 'ogg',
        'ogg': 'ogg'
    };

    var generateSources = function (url, mime) {
        return url.reduce(function (html, elem, index) {
            if(elem) {
                html.push('<source type="' + mime[index] + '" src="' + elem + '">');
            } 
            return html;
        }, []).join('/n');
    };

    module.image = function (url, mime, title) {
        if (url instanceof Array) {
            url = url[0];
        }

        module.show({
            title: title || 'Image',
            content: '<img src="' + url + '">',
            size: 'lg'
        });
    };

    module.video = function (url, mime, title) {
        var content = '';

        if (url instanceof Array) {
            content = '<video controls autoplay loop>' + generateSources(url, mime) + '</video>';

        } else {
            content = '<video src="' + url + '" controls autoplay loop></video>';
        }

        module.show({
            title: title || 'Video',
            content: content,
            size: 'lg'
        });
    };

    module.audio = function (url, mime, title) {
        var content = '';

        if (url instanceof Array) {
            content = '<audio controls autoplay loop>' + generateSources(url, mime) + '</audio>';
        } else {
            content = '<audio src="' + url + '" controls autoplay loop></audio>';
        }

        module.show({
            title: title || 'Audio',
            content: content,
            size: 'lg'
        });
    };

// if passed namespace does not exist, create one
    global[namespace] = global[namespace] || {};

// append module to given namespace
    global[namespace][moduleName] = module;

}(window, 'TrapperApp', 'Modal', jQuery));
