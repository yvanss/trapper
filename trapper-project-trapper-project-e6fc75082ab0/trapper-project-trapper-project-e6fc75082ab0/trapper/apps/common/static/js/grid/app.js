'use strict';
(function (angular) {

    angular.module('trapperGrid', ['ngSanitize', 'ngCookies', 'ngTable'])
        .config(['$interpolateProvider', function ($interpolateProvider) {

            $interpolateProvider.startSymbol('{[{');
            $interpolateProvider.endSymbol('}]}');

        }]).config(function ($httpProvider) {

            $httpProvider.defaults.transformRequest = function (data) {
                if (data === undefined) {
                    return data;
                }
                return $.param(data);
            };

            $httpProvider.defaults.headers.post['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8';

            $httpProvider.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest';

        }).run(['$http', '$cookies', function ($http, $cookies) {

            $http.defaults.headers.common['X-CSRFToken'] = $cookies.csrftoken;
            $http.defaults.headers.common['csrftoken'] = $cookies.csrftoken;

        }]);

}(angular));