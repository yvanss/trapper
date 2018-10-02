(function(window, angular) {
    'use strict';
    var trapperGrid = angular.module('trapperGrid');
    
    /* TRAPPER CUSTOM MODULES */

    var alert = window.TrapperApp.Alert,
    modal = window.TrapperApp.Modal,
    plugins = window.TrapperApp.Plugins;

    /* HELPER DIRECTIVES */

    // http://stackoverflow.com/questions/17470790/how-to-use-a-keypress-event-in-angularjs
    trapperGrid.directive('ngEnter', function () {
        return function (scope, element, attrs) {
            element.bind("keydown keypress", function (event) {
                if(event.which === 13) {
                    scope.$apply(function (){
                        scope.$eval(attrs.ngEnter);
                    });             
                    event.preventDefault();
                }
            });
        };
    });
    
    /* ACTION DIRECTIVES */

    trapperGrid.directive('actionMedia', function() {
        return {
            restrict: 'E',
            scope: true,
            replace: true,
            transclude: true,
            template: '<a href="#" ng-transclude class="img-thumbnail"></a>',
            link: function postLink(scope) {
                scope.execute = function($event, record) {
                    $event.stopPropagation();
                    $event.preventDefault();
                    
                    modal.media({
                        type: record.resource_type || record.resource.resource_type,
                        url: [
                            (record.resource) ? record.resource.url : record.url,
                            (record.resource) ? record.resource.extra_url : record.extra_url,
                        ],
                        mime: [
                            (record.resource) ? record.resource.mime : record.mime,
                            (record.resource) ? record.resource.extra_mime : record.extra_mime,
                        ]
                    });
                };
            }
        };
    });

    function removeAction(scope, url, records) {
        modal.confirm({
            title: 'Delete selected records',
            content: 'You have selected <strong>'+records.length+'</strong> record(s) to delete. '+
                'Are you sure you want to continue?',
            buttons: [{
                label: 'Yes',
                type: 'success',
                onClick: function() {
                    scope.remove(url, records);
                }
            }, {
                label: 'No',
                type: 'danger'
            }]
        });
    }

    trapperGrid.directive('actionRemove', function() {
        return {
            restrict: 'E',
            scope: true,
            replace: true,
            template: '<button class="btn btn-danger" title="Delete"><span class="fa fa-trash-o"></span></button>',
            link: function postLink(scope) {
                scope.execute = function($event, record) {
                    $event.stopPropagation();
                    removeAction(scope, record.delete_data, [record.pk]);
                };
            }
        };
    });

    var getPKS = function(scope) {
        return scope.data.selected.join(',');
    };
    var msg_zero_items_selected = 'You have to select at least one record to run this action.';
    var msg_processing = '<div class="alert alert-info"><span class="fa fa-cog fa-spin">'+
        '</span> Processing data</div>';
    var msg_server_error = 'Unexpected server error.';


    trapperGrid.directive('actionRemoveSelected', function() {
        return {
            restrict: 'E',
            scope: true,
            replace: true,
            template: '<a href="#" ng-disabled="!filters.owner">Delete selected</a>',
            link: function postLink(scope) {
                scope.execute = function($event, url) {
                    $event.preventDefault();
                    var records = scope.data.selected;
                    if(!records.length) {
                        alert.error(msg_zero_items_selected);
                        return;
                    }
                    removeAction(scope, url, records);
                };
            }
        };
    });

    trapperGrid.directive('actionApproveSelected', ['$http', function($http) {
        return {
            restrict: 'E',
            scope: true,
            replace: true,
            template: '<a href="#">Approve selected</a>',
            link: function postLink(scope) {
                scope.execute = function($event, url) {
                    $event.preventDefault();

                    var pks = getPKS(scope);
                    if(!pks.length) {
                        alert.error(msg_zero_items_selected);
                        return;
                    }

                    modal.confirm({
                        title: 'Approve selected user classifications',
                        content: 'You have selected <strong>'+scope.data.selected.length+'</strong> '+
                            ' user classification(s) to approve. Are you sure you want to continue?',
                        buttons: [{
                            label: 'Yes',
                            type: 'success',
                            hide: false,
                            onClick: function() {
                                $('.modal-body').prepend(msg_processing);
                                $http({
                                    method: 'POST',
                                    url: url,
                                    data: {pks: pks}
                                }).then(function(response) {
                                    if(!response.data.status) {
                                        alert.error(response.data.msg);
                                        modal.hideModal();
                                    } else {
                                        alert.success(response.data.msg);
                                        scope.load();
                                        modal.hideModal();
                                    }
                                }).catch(function(error) {
                                    modal.hideModal();
                                    alert.error(error || msg_server_error);
                                });
                            }
                        }, {
                            label: 'No',
                            type: 'danger'
                        }]
                    });                
                };
            }
        };
    }]);
    
    trapperGrid.directive('actionGenerateDataPackage', ['$http', function($http) {
        return {
            restrict: 'E',
            scope: true,
            replace: true,
            template: '<a href="#">Generate data package</a>',
            link: function postLink(scope) {
                scope.execute = function($event, url) {
                    $event.preventDefault();

                    var pks = getPKS(scope);
                    if(!pks.length) {
                        alert.error(msg_zero_items_selected);
                        return;
                    }

                    modal.external({
                        title: 'Generate data package',
                        url: url,
                        onShow: function($modal) {
                            var $form = $modal.find('form');
                            
                            $form.on('submit', function(e) {
                                e.preventDefault();
                                $form.prepend(msg_processing);                                  
                                $("#id_resources_pks").val(pks);
                                
                                $http({
                                    method: 'POST',
                                    url: url,
                                    data: $form.serializeArray()
                                }).then(function(response) {
                                    if(!response.data.success) {
                                        if(response.data.form_html) {
                                            $form.html(
                                                response.data.form_html
                                            );
                                        } else {
                                            alert.error(response.data.msg);
                                        }
                                    } else {
                                        alert.success(response.data.msg);
                                    }
                                    modal.hideModal();
                                }).catch(function(error) {
                                    modal.hideModal();
                                    alert.error(error || msg_server_error);
                                });
                            });
                        }
                    });

                };
            }
        };
    }]);

    trapperGrid.directive('actionUpdate', ['$http', function($http) {
        return {
            restrict: 'E',
            scope: true,
            replace: true,
            template: '<button class="btn btn-default" title="Update"><span class="fa fa-pencil"></span></button>',
            link: function postLink(scope) {
                scope.execute = function($event, record, redirect) {
                    $event.stopPropagation();
                    if(redirect) {
                        window.location =  record.update_data;
                        return;
                    }
                    modal.external({
                        title: 'Update',
                        url: record.update_data,
                        onShow: function($modal) {
                            var $form = $modal.find('form');
                            plugins.collapsable();
                            plugins.wysiwyg();
                            plugins.select2();
                            plugins.datepicker();
                            plugins.map();

                            $form.on('submit', function(e) {
                                e.preventDefault();
                                $form.prepend(msg_processing);                                
                                
                                $http({
                                    method: 'POST',
                                    url: $form.attr('action'),
                                    data: $form.serializeArray()
                                }).then(function(response) {
                                    if(!response.data.success) {
                                        $form.html(
                                            response.data.form_html
                                        );
                                        plugins.collapsable();
                                        plugins.wysiwyg();
                                        plugins.select2();
                                        plugins.datepicker();
                                        plugins.map();
                                        return;
                                    }
                                    alert.success(response.data.msg);
                                    scope.load();
                                    modal.hideModal();
                                }).catch(function(error) {
                                    modal.hideModal();
                                    alert.error(error || msg_server_error);
                                });
                            });
                        }
                    });
                };
            }
        };
    }]);
    
    trapperGrid.directive('actionBulkUpdate', ['$http', '$q', 'config', function($http, $q, config) {
        return {
            restrict: 'E',
            scope: true,
            replace: true,
            template: '<a href="#" ng-disabled="!filters.owner">Bulk update</a>',
            link: function postLink(scope) {
                
                scope.execute = function(url) {

                    var pks = getPKS(scope);
                    if(!pks.length) {
                        alert.error(msg_zero_items_selected);
                        return;
                    }
                    
                    modal.external({
                        title: 'Bulk update',
                        url: url,
                        onShow: function($modal) {
                            var $form = $modal.find('form');
                            plugins.select2();
                            plugins.datepicker();
                            plugins.lockerInputs();

                            $form.on('submit', function(e) {
                                e.preventDefault();
                                $form.prepend(msg_processing);                                
                                $("#id_records_pks").val(pks);
                                
                                $http({
                                    method: 'POST',
                                    url: url,
                                    data: $form.serializeArray()
                                }).then(function(response) {
                                    if(!response.data.success) {
                                        if(response.data.form_html) {
                                            $form.html(
                                                response.data.form_html
                                            );
                                            plugins.select2();
                                            plugins.datepicker();
                                            plugins.lockerInputs();
                                        } else {
                                            alert.error(response.data.msg);
                                            modal.hideModal();
                                        }
                                    } else {
                                        alert.success(response.data.msg);
                                        scope.load();
                                        modal.hideModal();
                                    }
                                }).catch(function(error) {
                                    modal.hideModal();
                                    alert.error(error || msg_server_error);
                                });
                            });
                        }
                    });
                };
            }
        };
    }]);

    trapperGrid.directive('actionCreateTags', ['$http', function($http) {
        return {
            restrict: 'E',
            scope: true,
            replace: true,
            template: '<a href="#" ng-disabled="!filters.owner">Create tags</a>',
            link: function postLink(scope) {
                
                scope.execute = function($event, url) {
                    $event.preventDefault();
                    
                    var pks = getPKS(scope);
                    
                    if(!pks.length) {
                        alert.error('To add tags select at least one approved classification. Also '+
                                   'you must have an update permission to add tags to given resource.');
                        return;
                    }
                    
                    modal.external({
                        title: 'Create tags',
                        url: url,
                        onShow: function($modal) {
                            var $form = $modal.find('form');
                            
                            $form.on('submit', function(e) {
                                e.preventDefault();
                                $("#id_classifications_pks").val(pks);
          
                                $http({
                                    method: 'POST',
                                    url: $form.attr('action'),
                                    data: $form.serializeArray()
                                }).then(function(response) {
                                    modal.hideModal();
                                    if(response.data.status) {
                                        alert.success(response.data.msg);
                                    } else {
                                        alert.error(response.data.msg);
                                    }
                                }).catch(function(error) {
                                    modal.hideModal();
                                    alert.error(error || msg_server_error);
                                });
                            });
                        },
                        size: 'sm'
                    });
                };
            }
        };
    }]);

    trapperGrid.directive('actionUpdateLocation', function() {
        return {
            restrict: 'E',
            scope: true,
            replace: true,
            template: '<button class="btn btn-default" title="Update with map"><span class="fa fa-pencil"></span></button>',
            link: function postLink(scope) {
                scope.execute = function($event, record) {
                    $event.stopPropagation();
                    
                    window.location =  record.update_data;
                };
            }
        };
    });

    trapperGrid.directive('actionDetails', function() {
        return {
            restrict: 'E',
            scope: true,
            replace: true,
            template: '<button class="btn btn-default" title="Details"><span class="fa fa-search"></span></button>',
            link: function postLink(scope) {
                scope.execute = function($event, record) {
                    $event.stopPropagation();
                    
                    window.open(record.detail_data);
                };
            }
        };
    });

    trapperGrid.directive('actionMap', function() {
        return {
            restrict: 'E',
            scope: true,
            replace: true,
            template: '<button class="btn btn-default" title="Show map"><span class="fa fa-globe"></span></button>',
            link: function postLink(scope) {
                scope.execute = function($event, record) {
                    $event.stopPropagation();
                    localStorage.setItem('trapper.geomap.filter', JSON.stringify([-1]));
                    window.location = record.detail_data;
                };
            }
        };
    });

    trapperGrid.directive('actionPermission', function() {
        return {
            restrict: 'E',
            scope: true,
            replace: true,
            template: '<button class="btn btn-primary" title="Ask for permission"><span class="fa fa-question"></span></button>',
            link: function postLink(scope) {
                scope.execute = function($event, record) {
                    $event.stopPropagation();
                    window.location = record.ask_access_data.url;
                };
            }
        };
    });
    
    function saveClassifyFilters(collection, deployments){
        var filters_data = {
            'collection_pk': collection,
            'filters': {
                'deployment': deployments
            }
        };
        localStorage.setItem('trapper.classify.settings', JSON.stringify(filters_data));
    }

    trapperGrid.directive('actionClassify', function () {
        return {
            restrict: 'E',
            scope: true,
            replace: true,
            template: '<button class="btn btn-default" title="Classify"><span class="fa fa-eye"></span></button>',
            link: function postLink(scope) {
                scope.execute = function (
                    $event, record, deployment_based_nav
                ) {
                    $event.stopPropagation();
                    if (!deployment_based_nav) {
                        localStorage.removeItem('trapper.classify.settings');
                        window.open(record.classify_data);
                    } else {
                        if (!record.resource.deployment) {
                            var deployments = [];
                            localStorage.removeItem('trapper.classify.settings');
                        } else {
                            var deployments = [record.resource.deployment];
                            saveClassifyFilters(record.collection, deployments);
                        }
                    }
                    if (!deployments.length) {
                        window.open(record.classify_data);
                    } else {
                        window.open(
                            record.classify_data + '?deployments=' + deployments.join(',')
                        ); 
                    }
                };
            }
        };
    });

    trapperGrid.directive('actionClassifyCollection', function () {
        return {
            restrict: 'E',
            scope: true,
            replace: true,
            template: '<button class="btn btn-default" title="Classify"><span class="fa fa-eye"></span></button>',
            link: function postLink(scope) {
                scope.execute = function (
                    $event, record
                ) {
                    $event.stopPropagation();
                    if (typeof(scope.filters.deployments) !== 'undefined') {
                        var deployments = scope.filters.deployments[record.pk];
                    } else {
                        var deployments = []
                    }
                    saveClassifyFilters(record.pk, deployments);
                    if (!deployments.length) {
                        window.open(record.classify_data);
                    } else {
                        window.open(
                            record.classify_data + '?deployments=' + deployments.join(',')
                        ); 
                    }
                };
            }
        };
    });

    trapperGrid.directive('actionUserClassificationDetails', function() {
        return {
            restrict: 'E',
            scope: true,
            replace: true,
            template: '<button class="btn btn-default" title="Details"><span class="fa fa-search"></span></button>',
            link: function postLink(scope) {
                scope.execute = function (
                    $event, record, deployment_based_nav
                ) {
                    $event.stopPropagation();
                    if (!deployment_based_nav) {
                        localStorage.removeItem('trapper.classify.settings');
                        window.open(record.detail_data);
                    } else {
                        if (!record.resource.deployment) {
                            var deployments = [];
                            localStorage.removeItem('trapper.classify.settings');
                        } else {
                            var deployments = [record.resource.deployment];
                            saveClassifyFilters(record.collection, deployments);
                        }
                    }
                    if (!deployments.length) {
                        window.open(record.detail_data);
                    } else {
                        window.open(
                            record.detail_data + '?deployments=' + deployments.join(',')
                        ); 
                    }
                };
            }
        };
    });
    
    trapperGrid.directive('actionWarning', function() {
        return {
            restrict: 'E',
            scope: true,
            replace: true,
            template: '<button class="btn btn-warning" title="Warning"><span class="fa fa-exclamation-triangle"></span></button>',
            link: function postLink(scope) {
                scope.execute = function($event, content, record) {
                    $event.stopPropagation();
                    
                    modal.alert({
                        title: 'Warning',
                        content: content
                    });
                };
            }
        };
    });

    var doc = window.document;
    function c(k){
        return(doc.cookie.match('(^|; )'+k+'=([^;]*)')||0)[2];
    }

    function sendPost(url, fields) {
        var form = doc.createElement('form'),
        csrf = doc.createElement('input');
        
        form.method = 'POST';
        form.action = url;
        
        fields.forEach(function(field) {
            var input = doc.createElement('input');
            input.type = 'hidden';
            input.name = field.name;
            input.value = field.value;
            
            form.appendChild(input);
        });
        
        csrf.type = 'hidden';
        csrf.name = 'csrfmiddlewaretoken';
        csrf.value = c('csrftoken');
        
        form.appendChild(csrf);
        
        doc.body.appendChild(form);
        
        form.submit();
    }
    
    trapperGrid.directive('actionCreateCollection', ['$http', function($http) {
        return {
            restrict: 'E',
            scope: true,
            replace: true,
            template: '<button class="btn btn-success">Create collection</button>',
            link: function postLink(scope) {
                
                scope.execute = function(url, app) {

                    var pks = getPKS(scope);
                    if(!pks.length) {
                        alert.error(msg_zero_items_selected);
                        return;
                    }
                    
                    modal.external({
                        title: 'Create collection',
                        url: url + '?app=' + app,
                        onShow: function($modal) {
                            var $form = $modal.find('form');
                            plugins.select2();
                            plugins.wysiwyg();

                            $form.on('submit', function(e) {
                                e.preventDefault();
                                $form.prepend(msg_processing);                                
                                $("#id_resources_pks").val(pks);
                                $("#id_app").val(app);
                                
                                $http({
                                    method: 'POST',
                                    url: $form.attr('action'),
                                    data: $form.serializeArray()
                                }).then(function(response) {
                                    if(!response.data.success) {
                                        $form.html(
                                            response.data.form_html
                                        );
                                        plugins.select2();
                                        plugins.wysiwyg();
                                        return;
                                    }
                                    window.location = response.data.url;
                                }).catch(function(error) {
                                    modal.hideModal();
                                    alert.error(error || msg_server_error);
                                });
                            });
                        }
                    });
                };
            }
        };
    }]);
    
    trapperGrid.directive('actionAddtoCollection', ['$http', function($http) {
        return {
            restrict: 'E',
            scope: true,
            replace: true,
            template: '<a href="#">Add to Collection</a>',
            link: function postLink(scope) {
                scope.execute = function($event, url, urlList, app) {

                    var pks = getPKS(scope);      
                    if(!pks.length) {
                        alert.error(msg_zero_items_selected);
                        return;
                    }

                    $http.get(urlList).then(function(result) {
                        if(result && result.data) {
                            modal.confirm({
                                title: 'Choose collection',
                                content: buildSelect(result.data),
                                buttons: [{
                                    label: 'Save',
                                    type: 'success',
                                    hide: false,
                                    onClick: function($modal) {

                                        $('.modal-body').prepend(msg_processing);
                                        var collection = $modal.find('select[name="collection"]').val();
                                        
                                        if(collection.length) {
                                            sendPost(url, [{
                                                name: 'resources',
                                                value: pks
                                            }, {
                                                name: 'collection',
                                                value: collection
                                            }, {
                                                name: 'app',
                                                value: app                                                
                                            }]);
                                        }
                                    }
                                }],
                                onShow: function() {
                                    plugins.select2();
                                }
                            });
                        }
                    });
                };

                function buildSelect(data) {
                    var options = [];
                    
                    options = data.map(function(record) {
                        return '<option value="' + record.pk + '">' + record.name + '</option>';
                    });
                    
                    var content = '<div id="div_id_collection" class="form-group">'+
                        '<label for="id_collection" class="control-label  requiredField">'+
                        'Collection<span class="asteriskField">*</span></label>'+ 
                        '<div class="controls">'+ 
                        '<select id="id_collection" class="select2-default form-control" name="collection">' + options.join('\n') + '</select>'+
                        '<p class="help-block">You have to be an owner or manager of a collection to be able to add new resources to it.</p>'+
                        '</div>';
                    return content
                }                
            }
        };
    }]);
    
    trapperGrid.directive('actionAddtoResearch', ['$http', function($http) {
        return {
            restrict: 'E',
            scope: true,
            replace: true,
            template: '<a href="#">Add to Research project</a>',
            link: function postLink(scope) {
                scope.execute = function($event, url, urlList) {

                    var pks = getPKS(scope);
                    if(!pks.length) {
                        alert.error(msg_zero_items_selected);
                        return;
                    }
                    
                    $http.get(urlList).then(function(result) {
                        if(result && result.data) {
                            modal.confirm({
                                title: 'Choose research project',
                                content: buildSelect(result.data),
                                buttons: [{
                                    label: 'Save',
                                    type: 'success',
                                    onClick: function($modal) {
                                        var project = $modal.find('select[name="project"]').val();
                                        
                                        if(project.length) {
                                            sendRequest(url, project, pks);
                                        }
                                    }
                                }],
                                onShow: function() {
                                    plugins.select2();
                                }
                            });
                        }
                    });
                };
                
                function buildSelect(data) {
                    var options = [];
                    
                    options = data.results.map(function(record) {
                        return '<option value="' + record.pk + '">' + record.name + '</option>';
                    });
                    
                    return '<select class="select2-default" name="project">' + options.join('\n') + '</select>';
                }
                
                function sendRequest(url, project, pks) {
                    return $http({
                        method: 'POST',
                        url: url,
                        data: {
                            pks: pks,
                            research_project: project
                        }
                    }).then(function(response) {
                        if(!response.data.status) {
                            throw new Error(response.data.msg);
                        }
                        
                        alert.success('Selected collections have been added to the research project.');
                    }).catch(function(error) {
                        alert.error(error || msg_server_error);
                    });
                }
            }
        };
    }]);

    trapperGrid.directive('actionAddtoClassification', ['$http', function($http) {
        return {
            restrict: 'E',
            scope: true,
            replace: true,
            template: '<a href="#">Add to Classification project</a>',
            link: function postLink(scope) {
                scope.execute = function($event, url, urlList) {

                    var pks = getPKS(scope);
                    if(!pks.length) {
                        alert.error(msg_zero_items_selected);
                        return;
                    }
                    
                    $http.get(urlList).then(function(result) {
                        if(result && result.data) {
                            modal.confirm({
                                title: 'Choose a classification project',
                                content: buildSelect(result.data),
                                buttons: [{
                                    label: 'Save',
                                    type: 'success',
                                    onClick: function($modal) {
                                        var project = $modal.find('select[name="project"]').val();
                                        
                                        if(project.length) {
                                            sendRequest(url, project, pks);
                                        }
                                    }
                                }],
                                onShow: function() {
                                    plugins.select2();
                                }
                            });
                        }
                    });
                };
                
                function buildSelect(data) {
                    var options = [];
                    
                    options = data.results.map(function(record) {
                        return '<option value="' + record.pk + '">' + record.name + '</option>';
                    });
                    
                    return '<select class="select2-default" name="project">' + options.join('\n') + '</select>';
                }
                
                function sendRequest(url, project, pks) {
                    return $http({
                        method: 'POST',
                        url: url,
                        data: {
                            pks: pks,
                            classification_project: project
                        }
                    }).then(function(response) {
                        if(!response.data.status) {
                            throw new Error(response.data.msg);
                        }
                        
                        alert.success('Selected collections have been added to the classification project');
                    }).catch(function(error) {
                        alert.error(error || msg_server_error);
                    });
                }
            }
        };
    }]);

    trapperGrid.directive('actionDefinePrefix', ['$http', function($http) {
        return {
            restrict: 'E',
            scope: true,
            replace: true,
            template: '<a href="#" ng-disabled="!filters.owner">Define prefix</a>',
            link: function postLink(scope) {

                function sendRequest(url, prefix, append, pks) {
                    return $http({
                        method: 'POST',
                        url: url,
                        data: {
                            pks: pks,
                            custom_prefix: prefix,
                            append: append
                        }
                    }).then(function(response) {
                        if(!response.data.status) {
                            throw new Error(response.data.msg);
                        }
                        
                        alert.success('Prefix defined: ' + prefix);
                        
                        return response.data.changed;
                    }).catch(function(error) {
                        alert.error(error || msg_server_error);
                    });
                }

                scope.execute = function($event, url) {
                    $event.preventDefault();

                    var pks = getPKS(scope);
                    if(!pks.length) {
                        alert.error(msg_zero_items_selected);
                        return;
                    }

                    modal.confirm({
                        title: 'Define prefix',
                        content: [
                            '<label class="checkbox-inline"><input type="checkbox"> Append location ID</label>',
                            '<input type="text" class="form-control" placeholder="Define your prefix">'
                        ].join('\n'),
                        size: 'sm',
                        buttons: [{
                            label: 'Save',
                            type: 'success',
                            onClick: function($modal) {
                                var prefix = $modal.find('input[type="text"]').val();
                                var append = $modal.find('input[type="checkbox"]').prop('checked');
                                
                                if(prefix.length || append) {
                                    sendRequest(url, prefix, append, pks).then(function(){
                                        scope.load(); 
                                    }).catch(function(error) {
                                        alert.error(error || msg_server_error);
                                    });
                                }
                            }
                        }]
                    });
                };
            }
        };
    }]);
    
    trapperGrid.directive('actionShowMap', function() {
        return {
            restrict: 'E',
            scope: true,
            replace: true,
            transclude: true,
            template: ['<div class="btn-group">',
                       '<button type="button" class="btn btn-default" ng-disabled="!data.selectedCounter">',
                       '<span class="fa fa-globe"></span> Show on map</button>',
                       '<button type="button" class="btn btn-default dropdown-toggle" data-toggle="dropdown"',
                       ' ng-disabled="!data.selectedCounter">',
                       '<span class="fa fa-angle-down"></span>',
                       '</button>',
                       '<div class="dropdown-menu plain">',
                       '<ng-transclude></ng-transclude>',
                       '</div></div>'].join('\n'),
            link: function postLink(scope, element, attrs) {
                var btn = element.find('button:nth-child(1)');
                var select = element.find('select');
                
                select.select2().on('select2-selecting', function(event) {
                    execute(event.val);
                });
                
                btn.on('click', function() {
                    execute(attrs.url);
                });

                function getFields(fieldName, fieldPk) {
                    var fields = {}
                    var records = scope.data.records.filter(
                        function(record) {
                            return scope.data.selected.indexOf(record.pk) != -1
                        }
                    );
                    records.forEach(function(record){
                        fields[record[fieldPk]] = record[fieldName]
                    })
                    return fields;
                }
                
                function execute(url) {
                    localStorage.setItem('trapper.geomap.source', attrs.type);
                    if(attrs.type === 'collections') {
                        var fields = getFields('name', attrs.field)
                        var pks = Object.keys(fields)
                        localStorage.setItem('trapper.geomap.collections_names', JSON.stringify(fields));
                        localStorage.setItem('trapper.geomap.filter', JSON.stringify(pks));
                    } else {
                        localStorage.setItem('trapper.geomap.filter', JSON.stringify(scope.data.selected));
                    }
                    window.location = url;
                }
            }
        };
    });
    
    function sendRequest($http, url, flag, pks) {
        return $http({
            method: 'POST',
            url: url,
            data: {
                pks: pks
            }
        }).then(function(response) {
            if(!response.data.status) {
                throw new Error(response.data.msg);
            }
            
            return response.data.changed;
        });
    }

    trapperGrid.directive('actionUnlinkSelected', ['$http', function($http) {
        return {
            restrict: 'E',
            scope: true,
            replace: true,
            template: '<a href="#">Remove from collection</a>',
            link: function postLink(scope) {

                scope.execute = function($event, url) {
                    $event.preventDefault();
                    
                    var pks = getPKS(scope);                    
                    if(!pks.length) {
                        alert.error(msg_zero_items_selected);
                        return;
                    }

                    modal.confirm({
                        title: 'Remove resources',
                        content: 'Are you sure you want to remove '+
                            scope.data.selected.length +' selected resource(s) from this collection?',
                        buttons: [{
                            label: 'Yes',
                            type: 'success',
                            onClick: function() {
                                alert.info(
                                    'Selected resources are being removed from this collection now. Do not leave '+
                                        'this page until the proccess is over.'
                                );
                                scope.status.deleting = true;
                                sendRequest($http, url, true, pks).then(function() {
                                    alert.success('Selected resources have been removed from this collection.');
                                    scope.status.deleting = false;
                                    scope.load();
                                }).catch(function(error) {
                                    scope.status.deleting = false;
                                    scope.load();
                                    alert.error(error || msg_server_error);
                                });
                            }
                        }, {
                            label: 'No',
                            type: 'danger'
                        }]
                    });
                };
            }
        };
    }]);
    
    trapperGrid.directive('actionUnlink2Selected', ['$http', function($http) {
        return {
            restrict: 'E',
            scope: true,
            replace: true,
            template: '<a href="#">Remove from this project</a>',
            link: function postLink(scope) {
                
                scope.execute = function($event, url) {
                    $event.preventDefault();
                    
                    var pks = getPKS(scope);                    
                    if(!pks.length) {
                        alert.error(msg_zero_items_selected);
                        return;
                    }
                    
                    modal.confirm({
                        title: 'Remove project collections',
                        content: 'Are you sure you want to remove '+
                            scope.data.selected.length+' selected collection(s) from this project?',
                        buttons: [{
                            label: 'Yes',
                            type: 'success',
                            onClick: function() {
                                alert.info(
                                    'Selected collections are being removed from this project now. Do not leave '+
                                        'this page until the proccess is over.'
                                );
                                scope.status.deleting = true;
                                sendRequest($http, url, true, pks).then(function() {
                                    alert.success('Selected collections have been removed from this project.');
                                    scope.status.deleting = false;
                                    scope.load();
                                }).catch(function(error) {
                                    scope.status.deleting = false;
                                    scope.load();
                                    alert.error(error || msg_server_error);
                                });
                            }
                        }, {
                            label: 'No',
                            type: 'danger'
                        }]
                    });
                };
            }
        };
    }]);
    
    trapperGrid.directive('actionBulkCreateDeployments', ['$http', function($http) {
        return {
            restrict: 'E',
            scope: true,
            replace: true,
            template: '<a href="#">Add deployments</a>',
            link: function postLink(scope) {

                scope.execute = function(url) {

                    var pks = getPKS(scope);                    
                    if(!pks.length) {
                        alert.error(msg_zero_items_selected);
                        return;
                    }
                    
                    modal.external({
                        title: 'Add deployments',
                        url: url,
                        onShow: function($modal) {
                            var $form = $modal.find('form');
                            
                            plugins.select2();
                            plugins.datepicker();

                            $form.on('submit', function(e) {
                                e.preventDefault();
                                $form.prepend(msg_processing);
                                $('#id_locations_pks').val(pks);

                                $http({
                                    method: 'POST',
                                    url: $form.attr('action'),
                                    data: $form.serializeArray()
                                }).then(function(response) {
                                    if(!response.data.success) {
                                        $form.html(
                                            response.data.form_html
                                        );
                                        plugins.select2();
                                        plugins.datepicker();
                                        return;
                                    }                                    
                                    window.location = response.data.url;
                                }).catch(function(error) {
                                    modal.hideModal();
                                    alert.error(error || msg_server_error);
                                });
                            });
                        }
                    });
                };
            }
        };
    }]);

    // angular helper function (not public) to build querystring from js object   
    function forEachSorted(obj, iterator, context) {
        var keys = sortedKeys(obj);
        for (var i = 0; i < keys.length; i++) {
            iterator.call(context, obj[keys[i]], keys[i]);
        }
        return keys;
    }

    // angular helper function (not public) to build querystring from js object   
    function sortedKeys(obj) {
        var keys = [];
        for (var key in obj) {
            if (obj.hasOwnProperty(key)) {
                keys.push(key);
            }
        }
        return keys.sort();
    }

    // angular helper function (not public) to build querystring from js object   
    function encodeUriQuery(val, pctEncodeSpaces) {
        return encodeURIComponent(val).
            replace(/%40/gi, '@').
            replace(/%3A/gi, ':').
            replace(/%24/g, '$').
            replace(/%2C/gi, ',').
            replace(/%3B/gi, ';').
             replace(/%20/g, (pctEncodeSpaces ? '%20' : '+'));
    }
  
    // angular helper function (not public) to build querystring from js object   
    function buildUrl(url, params) {
        if (!params) return url;
        var parts = [];
        forEachSorted(params, function(value, key) {
            if (value === null || angular.isUndefined(value)) return;
            if (!angular.isArray(value)) value = [value];
            
            angular.forEach(value, function(v) {
                if (angular.isObject(v)) {
                    if (angular.isDate(v)) {
                        v = v.toISOString();
                    } else {
                        v = angular.toJson(v);
                    }
                }
                parts.push(encodeUriQuery(key) + '=' +
                           encodeUriQuery(v));
            });
        });
        if (parts.length > 0) {
            url += ((url.indexOf('?') == -1) ? '?' : '&') + parts.join('&');
        }
        return url;
    }

    trapperGrid.directive('actionExportWithFilters', function() {
        return {
            restrict: 'E',
            scope: true,
            replace: true,
            template: '<button class="btn btn-default"><span class="fa fa-download"></span> Export</button>',
            link: function postLink(scope) {
                scope.execute = function(url) {
                    window.open(buildUrl(url, scope.flattenFilters(scope.filters)));
                };
            }
        };
    });

    trapperGrid.directive('actionExportWithFiltersList', function() {
        return {
            restrict: 'E',
            scope: true,
            replace: true,
            template: '<a href="#"><span></span></a>',
            link: function postLink(scope, element, attrs) {
                var tag = element.find('span');
                tag[0].innerHTML = ' '+attrs.title;
                scope.execute = function(url) {
                    window.open(buildUrl(url, scope.flattenFilters(scope.filters)));
                };
            }
        };
    });

    trapperGrid.directive('actionBuildSequences', ['$http', function($http) {
        return {
            restrict: 'E',
            scope: true,
            replace: true,
            template: '<button class="btn btn-success"><span class="fa fa-cubes"></span> (Re)build sequences</button>',
            link: function postLink(scope) {
                                
                scope.execute = function(url) {

                    var pks = getPKS(scope);                    
                    if(!pks.length) {
                        alert.error(msg_zero_items_selected);
                        return;
                    }
                    
                    modal.external({
                        title: '(Re)build sequences',
                        url: url,
                        onShow: function($modal) {
                            var $form = $modal.find('form');
                            
                            $form.on('submit', function(e) {
                                e.preventDefault();                                
                                $("#id_collections_pks").val(pks);
                                
                                $http({
                                    method: 'POST',
                                    url: url,
                                    data: $form.serializeArray()
                                }).then(function(response) {
                                    if(!response.data.success) {
                                        if(response.data.form_html) {
                                            $form.html(
                                                response.data.form_html
                                            );
                                        } else {
                                            alert.error(response.data.msg);
                                        }
                                    } else {
                                        alert.success(response.data.msg);
                                    }
                                    modal.hideModal();
                                }).catch(function(error) {
                                    modal.hideModal();
                                    alert.error(error || msg_server_error);
                                });
                            });
                        }
                    });
                };
            }
        };
    }]);
    
/* FILTER DIRECTIVES */

trapperGrid.directive('filterDate', ['$timeout', 'config', function($timeout, cfg) {
    return {
        restrict: 'A',
        scope: {
            model: '=filterDate',
            name: '=filterName',
            filterService: '='
        },
        link: function postLink(scope, element) {
            var timeoutId;

            scope.model = {};

            scope.$on('filters:clear', function() {
                picker.find('input[type=text]').datepicker('setDate', '');
            });

            function update() {
                if(timeoutId) { $timeout.cancel(timeoutId); }

                timeoutId = $timeout(function() {
                    scope.filterService.updateFilter({
                        name: scope.name,
                        type: 'date',
                        value: scope.model
                    });
                }, 50);
            }

            var picker = $(element).datepicker({
                format: cfg.dateFormat.picker.toLowerCase(),
                clearBtn: true,
                autoclose: true,
                orientation: 'top right',
                todayHighlight: true
            });

            picker.on('changeDate', function(e) {
                scope.model = e.format();
                update();

            }).on('clearDate', function(e) {
                scope.model = '';
                update();
            });
        }
    };
}]);

trapperGrid.directive('filterDaterange', ['$timeout', 'config', function($timeout, cfg) {
    return {
        restrict: 'A',
        scope: {
            model: '=filterDaterange',
            name: '=filterName',
            filterService: '='
        },
        link: function postLink(scope, element) {
            var timeoutId;

            scope.model = {
                from: '',
                to: ''
            };

            scope.model = angular.extend(
                scope.model, scope.$parent.filters[scope.name]
            );

            scope.$on('filters:clear', function() {
                picker.find('input[type=text][placeholder=from]').datepicker('setDate', '');
                picker.find('input[type=text][placeholder=to]').datepicker('setDate', '');
            });

            scope.$on('filters:rebuild', function() {
                picker.find('input[type=text][placeholder=from]').datepicker(
                    'setDate',
                    scope.model.from
                );
                picker.find('input[type=text][placeholder=to]').datepicker(
                    'setDate',
                    scope.model.to
                );
            });

            function update() {
                if(timeoutId) { $timeout.cancel(timeoutId); }

                timeoutId = $timeout(function() {
                    scope.filterService.updateFilter({
                        name: scope.name,
                        type: 'daterange',
                        value: scope.model
                    });
                }, 50);
            }

            var picker = $(element).datepicker({
                format: cfg.dateFormat.picker.toLowerCase(),
                clearBtn: true,
                autoclose: true,
                orientation: 'top right',
                todayHighlight: true
            });

            picker.on('changeDate', function(e) {
                scope.model[e.target.placeholder] = e.format();
                update();

            }).on('clearDate', function(e) {
                scope.model[e.target.placeholder] = '';
                update();
            });
        }
    };
}]);

trapperGrid.directive('filterTimerange', ['$timeout', 'config', function($timeout, cfg) {
    return {
        restrict: 'A',
        scope: {
            model: '=filterTimerange',
            name: '=filterName',
            filterService: '='
        },
        link: function postLink(scope, element, attr) {
            var timeoutId;

            scope.model = {
                from: '',
                to: ''
            };

            scope.model = angular.extend(
                scope.model, scope.$parent.filters[scope.name]
            );

            scope.$on('filters:clear', function() {
                pickerFrom.timepicker('setTime', '');
                pickerTo.timepicker('setTime', '');
                scope.model = {};
            });

            scope.$on('filters:rebuild', function(){
                pickerFrom.timepicker(
                    'setTime',
                    scope.model.from
                );
                pickerTo.timepicker(
                    'setTime',
                    scope.model.to
                );
                //update();
            });

            function update() {
                if(timeoutId) { $timeout.cancel(timeoutId); }

                timeoutId = $timeout(function() {
                    scope.filterService.updateFilter({
                        name: scope.name,
                        type: 'timerange',
                        value: scope.model
                    });
                }, 50);
            }

            var inputs = $(element).find('input');
            var pickerFrom = $(inputs[0]).timepicker({
                show2400: cfg.timeFormat.is24,
                timeFormat: cfg.timeFormat.picker
            });
            var pickerTo = $(inputs[1]).timepicker({
                show2400: cfg.timeFormat.is24,
                timeFormat: cfg.timeFormat.picker
            });

            pickerFrom.on('change', function(e) {
                scope.model[e.target.placeholder] = e.target.value;
                update();
            });
            pickerTo.on('change', function(e) {
                scope.model[e.target.placeholder] = e.target.value;
                update();
            });
        }
    };
}]);

trapperGrid.directive('filterTokens', function() {
    return {
        restrict: 'A',
        scope: {
            filterService: '='
        },
        require: 'ngModel',
        link: function postLink(scope, element, attr, ctrl) {
            var filterName = attr.filterTokens;
            
            var select2 = $(element).select2({
                minimumResultsForSearch: 5,
                minimumInputLength: 3
            });

            scope.$on('filters:clear', function() {
                setTimeout(function() {
                    select2.val(null).trigger('change');
                }, 0);
            });

            scope.$on('filters:rebuild', function(){
                select2.val(scope.$parent.filters[filterName]).trigger('change');
            });

            scope.$watch(function() {
                return ctrl.$modelValue;
            }, function(newValue, oldValue) {
                if(newValue === oldValue) { return; }

                scope.filterService.updateFilter({
                    name: filterName,
                    type: 'array',
                    value: newValue
                });
            });
        }
    };
});

trapperGrid.directive('filterText', function() {
    return {
        restirct: 'A',
        require: 'ngModel',
        scope: {
            filterService: '='
        },
        link: function postLink(scope, element, attr, ctrl) {
            var     filterName = attr.filterText;
            var format = attr.filterFormat;

            // set default value - for selects actually
            ctrl.$setViewValue('');

            scope.$on('filters:clear', function() {
                ctrl.$setViewValue('');
                ctrl.$render();
            });

            scope.$watch(function() {
                return ctrl.$modelValue;
            }, function(newValue, oldValue) {
                if(newValue === oldValue) { return; }

                if(format && newValue) {
                    if(format === 'float') {
                        newValue = parseFloat(newValue, 10);
                    } else if(format === 'integer') {
                        newValue = parseInt(newValue, 10);
                    } else if(format === 'boolean') {
                        newValue = (newValue.toLowerCase() === 'true');
                    }
                }

                scope.filterService.updateFilter({
                    name: filterName,
                    type: 'text',
                    value: newValue,
                    exact: true
                });
            });
        }
    };
});

trapperGrid.directive('filterCheckbox', function() {
    return {
        restirct: 'A',
        require: 'ngModel',
        scope: {
            settings: '=filterCheckbox',
            filterService: '='
        },
        link: function postLink(scope, element, attr, ctrl) {
            var     filterName = scope.settings.name;

            scope.$on('filters:clear', function() {
                ctrl.$setViewValue(false);
                ctrl.$render();
            });

            scope.$watch(function() {
                return ctrl.$modelValue;
            }, function(newValue, oldValue) {
                if(newValue === oldValue) { return; }

                scope.filterService.updateFilter({
                    name: filterName,
                    type: 'text',
                    value: newValue ? scope.settings.value : '',
                    exact: true
                });
            });
        }
    };
});

trapperGrid.directive('filterHstore', ['$timeout', '$http', function($timeout, $http) {
    return {
        restirct: 'A',
        require: 'ngModel',
        scope: {
            filterService: '='
        },
        link: function postLink(scope, element, attr, ctrl) {
            var     filterName = attr.filterHstore;
            var timeoutId;

            scope.$on('filters:clear', function() {
                ctrl.$setViewValue('');
                ctrl.$render('');
            });

            var filter = function(value) {
                $http({
                    method: 'POST',
                    url: attr.url,
                    data: {
                        data: value,
                        field: attr.field,
                        module: attr.module
                    }
                }).then(function(response) {
                    if(!response.status) {
                        throw new Error(response.message);
                    } else {
                        scope.filterService.updateFilter({
                            name: filterName,
                            type: 'array',
                            value: response.records
                        });
                    }
                }).catch(function(error) {
                    alert.error(error.message || error);
                });
            };

            var validate = function(value) {
                var valid;

                try {
                    JSON.parse(value);
                    valid = true;
                } catch (e) {
                    valid = false;
                }

                element[(valid ? 'removeClass' : 'addClass')]('form-error');

                if(!value) {
                    element.removeClass('form-error');
                }

                return valid;
            };

            scope.$watch(function() {
                return ctrl.$modelValue;
            }, function(newValue, oldValue) {
                if(timeoutId) { $timeout.cancel(timeoutId); }

                timeoutId = $timeout(function() {
                    if(newValue === oldValue) { return; }

                    if(!validate(newValue)) {
                        return;
                    }

                    if(newValue.length < 5 && oldValue && oldValue.length < 5) {
                        newValue = '';
                        return;
                    }

                    filter(newValue);
                }, 250);
            });
        }
    };
}]);

trapperGrid.directive('filterSearch', ['$timeout', function($timeout) {
    return {
        restirct: 'A',
        require: 'ngModel',
        scope: {
            filterService: '='
        },
        link: function postLink(scope, element, attr, ctrl) {
            var     filterName = attr.filterSearch;
            var timeoutId;

            scope.$on('filters:clear', function() {
                ctrl.$setViewValue('');
                ctrl.$render('');
            });

            scope.$watch(function() {
                return ctrl.$modelValue;
            }, function(newValue, oldValue) {
                if(timeoutId) { $timeout.cancel(timeoutId); }

                timeoutId = $timeout(function() {
                    if(newValue === oldValue) { return; }

                    if(newValue.length < 3 && oldValue && oldValue.length < 3) {
                        newValue = '';
                    }

                    scope.filterService.updateFilter({
                        name: filterName,
                        type: 'text',
                        value: newValue
                    });
                }, 250);
            });
        }
    };
}]);

}(window, angular));
