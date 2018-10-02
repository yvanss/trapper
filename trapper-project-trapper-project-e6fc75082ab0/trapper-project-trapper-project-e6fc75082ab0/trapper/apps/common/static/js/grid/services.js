'use strict';

angular.module('trapperGrid').factory('config', function() {
    var service = {};

    service.listStatuses = {
        loading: '<span class="fa fa-cog fa-spin"></span> Loading data',
        deleting: '<span class="fa fa-cog fa-spin"></span> Deleting selected records',
        error: '<span class="fa fa-exclamation"></span> Requested data could not be loaded, please reload the page and try again',
        empty: '<span class="fa fa-info"></span> No results found'
    };

    service.dateFormat = {
        picker: 'DD.MM.YYYY',
        json: 'YYYY-MM-DD',
        table: 'DD.MM.YYYY, HH:mm:ss Z',
        simple: 'dd.MM.yyyy, HH:mm'
    };

    service.timeFormat = {
        is24: false,
        picker: 'H:i'
    };

    service.mediaIcons = {
        'A': '<span class="fa fa-file-audio-o fa-3x"></span>',
        'V': '<span class="fa fa-file-video-o fa-3x"></span>',
        'I': '<span class="fa fa-file-image-o fa-3x"></span>',
        default: '<span class="fa fa-file-o fa-3x"></span>'
    };

    service.classifiedIcons = {
        'true': '<span class="fa fa-check fa-2x"></span>',
        'false': '<span class="fa fa-close fa-2x"></span>'
    };

    service.optionList = {
        bool: [{
            value: '',
            label: 'All'
        }, {
            value: 'True',
            label: 'Yes',
        }, {
            value: 'False',
            label: 'No'
        }],
        progress: [{
            value: '',
            label: 'All'
        }, {
            value: '1',
            label: 'Ongoing',
        }, {
            value: '2',
            label: 'Finished'
        }],
        media: [{
            value: '',
            label: 'All'
        }, {
            value: 'I',
            label: 'Image',
        }, {
            value: 'A',
            label: 'Audio'
        }, {
            value: 'V',
            label: 'Video'
        }],
        status: [{
            value: '',
            label: 'All'
        }, {
            value: 'Public',
            label: 'Public'
        }, {
            value: 'Private',
            label: 'Private'
        }, {
            value: 'OnDemand',
            label: 'OnDemand'
        }],
        edit_status: [{
            value: '',
            label: '-'
        }, {
            value: 'Everyone can edit',
            label: 'Everyone'
        }, {
            value: 'Only editors can edit',
            label: 'Only editors'
        }, {
            value: 'Only owner can edit',
            label: 'Only owner'
        }],
        share_status: [{
            value: '',
            label: '-'
        }, {
            value: 'everyone (public)',
            label: 'everyone'
        }, {
            value: 'anyone with link',
            label: 'anyone with link'
        }, {
            value: 'Only owner can edit',
            label: 'editors only'
        }]
    };

    service.grid = {};
    service.grid.pageSizes = [10, 50, 100, 200, 500];
    service.grid.defaultSize = service.grid.pageSizes[0];

    service.columns = {
        resources: [
            '', 'Type', 'Name', 'Tags', 'Date recorded',
            'Owner', 'Actions'],
        collections: [
            'Name', 'Description', 'Status', 'Owner', 'Actions'],
        project_collections: [
            'Name', 'Status', 'Active', 'Total', 'Classified', 
            'Approved', 'Actions', 'Classify'],
        research_projects: [
            'Name', 'Acronym', 'Keywords', 'Actions'],
        classification_projects: [
            'Name', 'Research project', 'Status', 'Actions'],
        classifications: [
            '', 'Type', 'Name', 'Date recorded', 'Approved', 
            'Classification tags', 'Actions', 'Classify'
        ],
        user_classifications: [
            '', 'Type', 'Name', 'User', 'Updated', 'Approved', 
            'Classification tags', 'Actions'
        ],
        classificators: [
            'Name', 'Owner', 'Date updated', 'Actions'],
        locations: [
            'ID', 'Research project', 'Owner', 'Coordinates', 'Timezone', 
            'Country', 'State', 'County', 'City', 'Is public', 'Actions'
        ],
        deployments: [
            'ID', 'Location ID', 'Research project', 'Start', 'End', 
            'Corr. setup', 'Corr. tstamp', 'Owner', 'Actions'
        ],
        maps: [
            'Name', 'Description', 'Owner', 'Date updated', '', 'Actions'
        ]
    };

    return service;
});

angular.module('trapperGrid').factory('dataService', ['$http', '$q', function($http, $q) {
    var service = {};

    service.load = function(url, queryParams, pagination) {
        var pagination = (
            typeof pagination === 'undefined'
        ) ? true : pagination;

        return $http.get(
            url, 
            {
                params: queryParams 
            }
        ).then(function(res) {
            if(res && res.data) {
                return res.data;
            }
            return $q.reject('Invalid data returned');
        });
    };

    service.remove = function(url, records) {
        var pks = records.join(',');

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

            return response;
        });
    };

    return service;
}]);

angular.module('trapperGrid').factory('filterService', ['$filter', function($filter) {
    function Service(onUpdate) {
        this.filters = {};
        this.hasFilters = false;
        this.onUpdate = onUpdate || function() {};
    }

    Service.prototype.clearFilters = function() {
        this.filters = {};
        this.onUpdate('clear');
    };

    Service.prototype.rebuildFilters = function() {
        this.onUpdate('rebuild');
    };

    Service.prototype.updateFilter = function(filter) {
        var filterObj = this.filters[filter.name];

        if(!filterObj) {
            filterObj = this.filters[filter.name] = '';
        } else {
            filterObj.type = filter.type;
            filterObj.value = filter.value;
            filterObj.exact = filter.exact;
        }

        this.onUpdate(filterObj);
    };

    return {
        create: function(onUpdate) {
            return new Service(onUpdate);
        }
    };
}]);
