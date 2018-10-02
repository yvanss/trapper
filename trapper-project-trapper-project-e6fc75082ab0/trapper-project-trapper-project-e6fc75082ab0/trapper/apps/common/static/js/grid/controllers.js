'use strict';
(function(window, angular) {

var trapperGrid = angular.module('trapperGrid');

/* TRAPPER CUSTOM MODULES */
var alert = window.TrapperApp.Alert,
    modal = window.TrapperApp.Modal,
    plugins = window.TrapperApp.Plugins;


/* GRID CONTROLLER */
trapperGrid.controller('GridController',
                       ['$window', '$scope', 'config', 'dataService', 'filterService',
                        function($window, $scope, cfg, dataService, filterService) {

    $scope.data = {
        records: [],
        selected: [],
        request: {
            url: '',
            queryParams: {},
        },
        selectedCounter: 0,
        total: 0,
    };
    $scope.filters = {};

    $scope.pageSizes = cfg.grid.pageSizes;
    $scope.optionList = cfg.optionList;
    $scope.dateFormat = cfg.dateFormat;
    $scope.status = {
        error: false,
        loading: false
    };
    $scope.listStatuses = cfg.listStatuses;
    $scope.columns = cfg.columns;

    $scope.filter = filterService.create(function(updated) {
        if(updated === 'clear') {
            $scope.data.total = 0;
            $scope.data.request.queryParams = {};
            $scope.map_filters_applied = false;
            $scope.$broadcast('filters:clear');
            $scope.load();
        }
    });
    
    $scope.flattenFilters = function flattenObject(ob) {
	var toReturn = {};
	for (var i in ob) {
	    if (!ob.hasOwnProperty(i)) continue;	    
	    if ((typeof ob[i]) == 'object' && ob[i].constructor != Array) {
		var flatObject = flattenObject(ob[i]);
		for (var x in flatObject) {
		    if (!flatObject.hasOwnProperty(x)) continue;
		    
		    toReturn[i + '_' + x] = flatObject[x];
		}
	    } else {
		toReturn[i] = ob[i];
	    }
	}
	return toReturn;
    };

    $scope.select = function($event, record) {
        if($event && ['a', 'button'].indexOf($event.target.tagName.toLowerCase()) > -1) {
            return;
        }
        record.$selected = !record.$selected;
        if (record.$selected) {
            $scope.data.selected.push(record.pk);
            $scope.data.selectedCounter++;
        } else {
            var index = $scope.data.selected.indexOf(record.pk);
            $scope.data.selected.splice(index, 1);
            $scope.data.selectedCounter--;
        }
    };

    $scope.selectPage = function() {
        $scope.data.records.forEach( 
            function(item) {
                if($scope.data.selected.indexOf(item.pk) < 0) {
                    item.$selected = true;
                    $scope.data.selected.push(item.pk);
                    $scope.data.selectedCounter++;
                }            
            }
        );
    };                        

    $scope.selectAllFiltered = function() {
        $scope.status.error = false;
        $scope.status.loading = true;
        var queryParams = (angular.extend(
            {}, $scope.data.request.queryParams,
            {'all_filtered': true}
        ));
        dataService.load(
            $scope.data.request.url, queryParams, false
        ).then(function(data) {
            $scope.data.selected = data;
            $scope.data.selectedCounter = data.length;
            $scope.data.records.forEach( 
                function(item) {
                    if($scope.data.selected.indexOf(item.pk) > -1) {
                        item.$selected = true;
                    }
                }            
            );
        }).catch(function() {
            $scope.status.error = true;
        }).finally(function() {
            $scope.status.loading = false;
        });
    };

    $scope.clearSelection = function() {
        $scope.data.selected = [];
        $scope.data.records.forEach( 
            function(item) {
                item.$selected = false;
            }            
        );
        $scope.data.selectedCounter = 0;
    };                        

    $scope.filterOwner = function() {
        $scope.filters.owner = !$scope.filters.owner;
        $scope.load(
            $scope.data.request.url, {}, true
        );
    };

    $scope.load = function(url, queryParams, filterData, pagination) {
        url = (
            typeof url === 'undefined'
        ) ? $scope.data.request.url : url;
        queryParams = (
            typeof queryParams === 'undefined'
        ) ? {} : queryParams;
        filterData = (
            typeof filterData === 'undefined'
        ) ? false : filterData;
        pagination = (
            typeof pagination === 'undefined'
        ) ? true : pagination;


        $scope.status.error = false;
        $scope.status.loading = true;
    
        queryParams = (angular.extend(
            $scope.data.request.queryParams, queryParams
        ));

        if(filterData) {
            queryParams = angular.extend(
                queryParams,
                $scope.flattenFilters($scope.filters), 
                {page:1}
            );
        }

        // Filter items by location's pks sent from the map view  
        var locations = $window.localStorage.getItem('trapper.geomap.locations');
        $window.localStorage.removeItem('trapper.geomap.locations');

        if(locations) {
            $scope.map_filters_applied = true;
            queryParams = angular.extend(
                queryParams,
                {locations_map:locations}
            );
        }

        $scope.data.request = {
            url: url,
            queryParams: queryParams,
        };

        dataService.load(url, queryParams, pagination).then(function(data) {
            if(pagination) {
                $scope.data.records = data.results;
                $scope.data.pagination = data.pagination;

                if($scope.data.total === 0) {
                    $scope.data.total = $scope.data.pagination.count;
                }
            } else {
                $scope.data.records = data;
            }

            if($scope.data.selectedCounter > 0) {
                $scope.data.records.forEach( 
                    function(item) {
                        if($scope.data.selected.indexOf(item.pk) > -1) {
                            item.$selected = true;
                        }
                    }            
                );
            }            
        }).catch(function() {
            $scope.status.error = true;
        }).finally(function() {
            $scope.status.loading = false;
        });
    };

    $scope.remove = function(url, records) {
        alert.info(
            'Selected records are being removed now. Do not leave '+
                'this page until the proccess is over.'
        );
        $scope.status.deleting = true;
        dataService.remove(url, records).then(function(response) {
            if(response.data.status) {
                alert.success(response.data.msg);
            } else {
                alert.error(response.data.msg);
            }
            $scope.clearSelection();
            $scope.status.deleting = false;
            $scope.load();
        }).catch(function(error) {
            alert.error(error || 'Record(s) could not be deleted.');
            $scope.status.deleting = false;
        });
    };
}]);



/* SEQUENCES CONTROLLER */

trapperGrid.controller('SequenceController',
            ['$interpolate', '$window', '$scope', 'config', 'dataService', 'filterService', '$http', '$controller',
            function($interpolate, $window, $scope, cfg, dataService, filterService, $http, $controller) 
{
    angular.extend(this, $controller('GridController', {$scope: $scope}));

    $scope.sequenceSizes = [2,5,10,50,100,500];
    $scope.filters = {
        size: 5   
    };
    $scope.sequences = {
        original: [],
        selected: null
    };
    $scope.data.request = {
        queryParams: {},
        urlRes: '',
        urlSeq: ''
    };

    $scope.load_resources = function(url, queryParams, filterData) {
        url = (
            typeof url === 'undefined'
        ) ? $scope.data.request.urlRes : url;
        queryParams = (
            typeof queryParams === 'undefined'
        ) ? {} : queryParams;
        filterData = (
            typeof filterData === 'undefined'
        ) ? false : filterData;

        $scope.status.error = false;
        $scope.status.loading = true;
    
        queryParams = angular.extend(
            $scope.data.request.queryParams, queryParams
        );

        if(filterData) {
            queryParams = angular.extend(
                queryParams,
                $scope.flattenFilters($scope.filters) 
            );
        }

        $scope.data.request.urlRes = url;
        $scope.data.request.queryParams = queryParams;

        dataService.load(url, queryParams, true).then(function(data) {
            $scope.data.records = data.results;
            $scope.data.pagination = data.pagination; 

            if($scope.data.selectedCounter > 0) {
                $scope.data.records.forEach( 
                    function(item) {
                        if($scope.data.selected.indexOf(item.pk) > -1) {
                            item.$selected = true;
                        }
                    }            
                );
            }
            setTimeout(function() {
                $('.btn-current').trigger('click');
            }, 0);
        }).catch(function() {
            $scope.status.error = true;
        }).finally(function() {
            $scope.status.loading = false;
        });
    };

    $scope.load_sequences = function(url) {
        url = (
            typeof url === 'undefined'
        ) ? $scope.data.request.urlSeq : url;

        $scope.status.error = false;
        $scope.status.loading = true;
        
        $scope.data.request.urlSeq = url;

        var params = {
            deployment: $scope.filters.deployment
        };

        dataService.load(url, params, false).then(
            function(data) {
                $scope.sequences.original = [
                    { blank: true, sequence_id: 'New', resources: [], description: '' }
                ].concat(data);
                $scope.sequences.selected = $scope.sequences.original[0];
                setTimeout(function() {
                    $('#sequence-picker').select2();
                }, 0); // :(((                
            }).catch(function() {
                $scope.status.error = true;
            }).finally(function() {
                $scope.status.loading = false;
            });
    };

    $scope.load = function(urlRes, urlSeq, current, collection_pk) {
        $scope.status.loading = true;
        
        $scope.data.collection_pk = collection_pk;        
        $scope.current = current;
        
        var filters_data = $scope.getSavedFilters();
        if(filters_data) {
            $scope.filters = angular.extend(
                $scope.filters, filters_data.filters);
        }

        $scope.load_sequences(urlSeq);
        $scope.load_resources(urlRes, {}, true);
        setTimeout(function() {
            $scope.filter.rebuildFilters();
        }, 0);

    };               
    
    $scope.reload = function() {
        $scope.load_sequences();
        $scope.load_resources(
            $scope.data.request.Resurl,
            $scope.data.request.queryParams,
            true
        );
    };

    function getSelected() {
        return $scope.data.selected.join(',');
    }

    $scope.select = function($event, record) {
        if($event && ['a', 'button'].indexOf($event.target.tagName.toLowerCase()) > -1) {
            return;
        }

        record.$selected = !record.$selected;
        if (record.$selected) {
            $scope.data.selected.push(record.pk);
            $scope.data.selectedCounter++;
        } else {
            var index = $scope.data.selected.indexOf(record.pk);
            $scope.data.selected.splice(index, 1);
            $scope.data.selectedCounter--;
        }

        var selected = getSelected();

        $('#id_selected_resources').val(selected);
        var btn = $('#classify-multiple');
        btn.prop('disabled', selected.length == 0);
        $('#id_selected_resources').val(selected);
        var btn2 = $('#approve-multiple');
        btn2.prop('disabled', selected.length == 0);
    };

    $scope.clearSelection = function() {
        $scope.data.selected = [];
        $scope.data.records.forEach( 
            function(item) {
                item.$selected = false;
            }            
        );
        $scope.data.selectedCounter = 0;
        $('#id_selected_resources').val('');
    };                        

    $scope.sequenceChanged = function() {
        var s = $scope.sequences.selected;

        $scope.data.records.forEach(function(seq) {
            if(s.resources.indexOf(seq.pk) > -1) {
                seq.$selected = true;
            } else {
                seq.$selected = false;
            }
        });

        $scope.data.selected = [];
        $scope.data.selectedCounter = s.resources.length;
        s.resources.forEach( 
            function(item) {
                $scope.data.selected.push(item);
            }            
        );

        var selected = getSelected();

        $('#id_selected_resources').val(selected);
        var btn = $('#classify-multiple');
        btn.prop('disabled', selected.length == 0);        
    };

    $scope.filter = filterService.create(function(updated) {
        if(updated === 'clear') {
            localStorage.removeItem('trapper.classify.settings');
            $scope.$broadcast('filters:clear');
            setTimeout(function() {
                $scope.reload();
            }, 0);           
            alert.info('Filters cleared.');
        }
        if(updated === 'rebuild') {
            $scope.$broadcast('filters:rebuild');
        }
    });

    $scope.saveFilters = function() {
        var filters_data = {
            collection_pk: $scope.data.collection_pk,
            filters: $scope.filters,
        };
        localStorage.setItem('trapper.classify.settings', JSON.stringify(filters_data));
        alert.info('Filters saved.');
    };

    $scope.getSavedFilters = function() {
        var filters_data = JSON.parse(localStorage.getItem('trapper.classify.settings'));
        if (filters_data && filters_data.collection_pk == $scope.data.collection_pk) {
            return filters_data;
        } else {
            return null;
        }    
    };

    $scope.saveSequence = function(url) {
        var s = $scope.sequences.selected;

        var resources = getSelected();
        if(!resources.length) {
            alert.warning('Cannot save empty sequence');
            return;
        }

        if(!s.blank) {
            $http({
                method: 'POST',
                url: url,
                data: {
                    pk: s.pk,
                    description: s.description,
                    resources: resources,
                    collection_pk: $scope.data.collection_pk,
                }
            }).then(function(response) {
                var seq = response.data.record;

                if(!seq) {
                    alert.error('Could not create sequence. '+ response.data.msg);
                    return;
                }

                Object.keys(seq).forEach(function(field) {
                    if(s[field]) {
                        s[field] = seq[field];
                    }
                });

                $scope.load_resources();
                alert.info('Sequence saved');
            });

            return;
        }

        modal.confirm({
            title: 'Create sequence',
            content: [
                '<form><div class="form-group"><label>Description</label>',
                '<textarea class="form-control" placeholder="Description" name="description"></textarea></div></form>'
            ].join('\n'),
            buttons: [{
                label: 'Create',
                type: 'success',
                hide: false,
                onClick: function($modal) {
                    var $form = $modal.find('form');
                    modal.hideModal();

                    $http({
                        method: 'POST',
                        url: url,
                        data: {
                            description: $form.find('[name="description"]').val(),
                            resources: resources,
                            collection_pk: $scope.data.collection_pk,
                        }
                    }).then(function(response) {
                        if(response.data.record) {
                            $scope.sequences.original.push(response.data.record);
                            setTimeout(function() {  $('#sequence-picker').select2(); }, 0); // :(((
                            $scope.load_resources();

                            alert.info('Sequence created');
                        } else {
                            alert.error('Could not create sequence. '+ response.data.msg);
                        }
                    });
                }
            }, {
                label: 'Cancel',
                type: 'default'
            }]
        });
    };

    $scope.updateSequence = function(url) {
        var s = $scope.sequences.selected;

        modal.confirm({
            title: 'Update sequence',
            content: $interpolate([
                '<form><div class="form-group"><label>Sequence ID</label>',
                '<input type="text" class="form-control" placeholder="Sequence ID" value="{[{ sequence_id }]}" name="sequence_id" readonly></div>',
                '<div class="form-group"><label>Description</label>',
                '<textarea class="form-control" placeholder="Description" name="description">{[{ description }]}</textarea></div></form>'
            ].join('\n'))(s),
            buttons: [{
                label: 'Update',
                type: 'success',
                hide: false,
                onClick: function($modal) {
                    var $form = $modal.find('form');
                    modal.hideModal();

                    $http({
                        method: 'POST',
                        url: url,
                        data: {
                            pk: s.pk,
                            description: $form.find('[name="description"]').val(),
                            resources: getSelected(),
                            collection_pk: $scope.data.collection_pk,
                        }
                    }).then(function(response) {
                        var seq = response.data.record;

                        if(!seq) {
                            alert.error('Could not update a sequence.');
                            return;
                        }

                        Object.keys(seq).forEach(function(field) {
                            if(s[field]) {
                                s[field] = seq[field];
                            }
                        });

                        $scope.load_resources();
                        alert.info('Sequence updated');
                    });
                }
            }, {
                label: 'Cancel',
                type: 'default'
            }]
        });

    };

    $scope.deleteSequence = function(url) {
        var s = $scope.sequences.selected;

        modal.confirm({
            title: 'Are you sure you want to delete the sequence?',
            content: s.sequence_id,
            buttons: [{
                label: 'Delete',
                type: 'danger',
                onClick: function() {
                    $http({
                        method: 'POST',
                        url: url,
                        data: {
                            pks: s.pk
                        }
                    }).then(function(response) {
                        if(!response.data.status) {
                            alert.error('Could not delete sequence');
                            return;
                        }

                        var index = $scope.sequences.original.indexOf(s);
                        $scope.sequences.original.splice(index, 1);
                        $scope.sequences.selected = $scope.sequences.original[0]; // the blank one
                        $scope.load_resources();
                        setTimeout(function() {  $('#sequence-picker').select2(); }, 0); // :(((

                        alert.info('Sequence deleted');
                    });
                }
            }, {
                label: 'Cancel',
                type: 'default'
            }]
        });

    };

}]);

}(window, angular));
