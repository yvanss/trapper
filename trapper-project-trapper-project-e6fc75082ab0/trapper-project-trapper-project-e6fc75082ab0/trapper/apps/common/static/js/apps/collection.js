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

    module.edit = module.create = function () {
        plugins.select2();
        plugins.wysiwyg();
    };

    module.request = function () {
        plugins.wysiwyg();
    };

    module.upload = function () {
        plugins.fileInputs();
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
                title: 'Delete collection',
                content: 'Are you sure you want to delete this collection?',
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

    var buildSelect = function (data) {
        var options = [];
        if(data.results) {
            data = data.results;
        }
        options = data.map(function (record) {
            return '<option value="' + record.pk + '">' + record.name + '</option>';
        });

        return '<select class="select2-default" name="project">' + options.join('\n') + '</select>';
    };

    var addToResearch = function (pk, url, urlList) {
        function c(k) {
            return (doc.cookie.match('(^|; )' + k + '=([^;]*)') || 0)[2];
        }

        function sendRequest(url, project, pks) {
            var req = new XMLHttpRequest();
            var params = '';

            req.addEventListener('load', function () {
                alert.success('Added to research project');
            }, false);
            req.addEventListener('error', function (error) {
                alert.error(error || 'Could not add to research project.');
            }, false);

            params += 'pks=' + pks;
            params += '&research_project=' + project;
            params += '&csrfmiddlewaretoken=' + c('csrftoken');

            req.open('post', url, true);
            req.setRequestHeader('Content-type', 'application/x-www-form-urlencoded');
            req.send(params);
        }

        function showModal(event) {
            var data = JSON.parse(event.target.response);

            modal.confirm({
                title: 'Choose research project',
                content: buildSelect(data),
                buttons: [{
                    label: 'Save',
                    type: 'success',
                    onClick: function ($modal) {
                        var project = $modal.find('select[name="project"]').val();

                        if (project.length) {
                            sendRequest(url, project, [pk]);
                        }
                    }
                }],
                onShow: function () {
                    plugins.select2();
                }
            });
        }

        function showError() {

        }

        var req = new XMLHttpRequest();
        req.addEventListener('load', showModal, false);
        req.addEventListener('error', showError, false);

        req.open('get', urlList, true);
        req.send();
    };

    module.preview = function () {
        doc.getElementById('action-addto-research').addEventListener('click', function (event) {
            event.preventDefault();
            var data = event.target.dataset;
            addToResearch(data.pk, data.url, data.urllist);
        });
        deleteConfirm();
    };

// if passed namespace does not exist, create one
    global[namespace] = global[namespace] || {};

// append module to given namespace
    global[namespace][moduleName] = module;

}(window, 'TrapperApp', 'Collection'));
