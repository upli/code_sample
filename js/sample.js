angular.module('WebMis20.directives')
    .directive('colorizeRbCode', [function () {
    return {
        restrict: 'A',
        scope: {
            colorizeRbCode: '='
        },
        link: function (scope, element, attrs) {
            var result = [],
                rbList = scope.colorizeRbCode || [];
            rbList.forEach(function (item) {
                result.push('<span style="font-size: 150%; font-weight: bold; color: {0}">{1}</span>'
                    .format(item.color, item.code))
            });
            element.append(result.join(', '));
        }
    }
}])
    .directive("glyphOkRemove", function () {
    return {
        restrict: 'A',
        scope: {
            key: '=glyphOkRemove',
            glyphTooltip: '@glyphTooltip'
        },
        link: function (scope, element, attributes) {
            var elem = $(element),
                glyph;

            if (scope.key) {
                glyph = $('<span class="glyphicon glyphicon-ok text-success"></span>');
            } else {
                glyph = $('<span class="glyphicon glyphicon-remove text-danger"></span>');
            }
            glyph.attr('title', scope.glyphTooltip);
            elem.before(glyph);
        }
    }
})
    .directive('wmWeekSwitch', [function () {
    return {
        restrict: 'E',
        replace: true,
        scope: {
            ngModel: '='
        },
        template: '\
        <div class="input-group" style="width: 220px">\
            <span class="input-group-btn">\
                <button type="button" class="btn btn-default" ng-click="prevWeek()">\
                    <i class="glyphicon glyphicon-arrow-left"></i>\
                </button>\
                <span class="btn btn-default" style="color: black" disabled>\
                    [[getFormattedWeek()]]\
                </span>\
                <button type="button" class="btn btn-default" ng-click="nextWeek()">\
                    <i class="glyphicon glyphicon-arrow-right"></i>\
                </button>\
            </span>\
        </div>',
        link: function(scope, element, attr) {
            var dateMonthFormat = 'DD.MM';

            function addWeek(date, weeks) {
                return moment(date).add(weeks, 'weeks').toDate();
            }

            scope.prevWeek = function () {
                scope.ngModel = addWeek(scope.ngModel, -1);
            };
            scope.nextWeek = function () {
                scope.ngModel = addWeek(scope.ngModel, 1);
            };
            scope.getFormattedWeek = function () {
                var startOfWeek = moment(scope.ngModel).startOf('isoWeek').format(dateMonthFormat),
                    endOfWeek = moment(scope.ngModel).endOf('isoWeek').format(dateMonthFormat);
                return '{0} - {1}'.format(startOfWeek, endOfWeek)
            }
        }
    };
}]);
