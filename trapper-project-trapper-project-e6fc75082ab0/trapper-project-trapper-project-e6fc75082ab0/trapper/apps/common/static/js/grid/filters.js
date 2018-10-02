(function () {

    'use strict';

    angular.module('trapperGrid').filter('round', function () {
        return function (input, method) {
            if (!method || !Math[method]) {
                method = 'round';
            }

            return Math[method](input);
        };
    });

    angular.module('trapperGrid').filter('latlng', function () {
        return function (input) {
            var latlng = input.split(' ');

            return parseFloat(latlng[2].slice(0, -1), 10).toFixed(5) + ', ' + parseFloat(latlng[1].slice(1), 10).toFixed(5);
        };
    });


    angular.module('trapperGrid').filter('typesIcon', ['$sce', 'config', function ($sce, cfg) {
        return function (input) {
            return $sce.trustAsHtml(cfg.mediaIcons[input] || cfg.mediaIcons.default);
        };
    }]);

    angular.module('trapperGrid').filter('classifiedIcons', ['$sce', 'config', function ($sce, cfg) {
        return function (input) {
            return $sce.trustAsHtml(cfg.classifiedIcons[input]);
        };
    }]);

// use moment to show datetime with appropriate timezone
    angular.module('trapperGrid').filter('dateTZ', function () {
        return function (input, format) {
            var timezone = input.substr(input.length - 6).replace(':','');
            return moment(input).utcOffset(timezone).format(format);
        };
    });

// remove offset from date field
// 2009-11-19T07:55:24+03:00 -> 2009-11-19T07:55:24
    angular.module('trapperGrid').filter('removeTimezone', function () {
        return function (input) {
            return input.substr(0, 19);
        };
    });

    function getNode(object, path) {
        var steps = path.split('.');
        var node = object[steps[0]] || null;

        if (steps.length === 1) {
            return node;
        }

        for (var i = 1; i < steps.length; i++) {
            node = node[steps[i]];

            if (!node) {
                return null;
            }
        }

        return node || null;
    }

    angular.module('trapperGrid').filter('inArray', function () {
        return function (input, values, name) {
            return input.filter(function (elem) {
                var recordValue = getNode(elem, name);

                if (!recordValue) {
                    return false;
                }

                if (!angular.isArray(recordValue)) {
                    recordValue = [recordValue];
                }

                for (var i = 0, len = recordValue.length; i < len; i++) {
                    if (values.indexOf(recordValue[i]) > -1) {
                        return true;
                    }
                }

                return false;
            });
        };
    });
}());
