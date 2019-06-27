'use strict';

WebMis20
.run(['$templateCache', function ($templateCache) {
    $templateCache.put(
        '/WebMis20/modal/client/diet_edit.html',
'<div class="modal-header">\
    <h3 class="modal-title">Сведения о диетах</h3>\
</div>\
<div class="modal-body">\
    <div class="alert alert-danger" ng-if="invalid_dates">Даты диет не должны пересекаться</div>\
    <ng-form name="modalForm">\
    <table class="table table-condensed">\
        <thead>\
        <tr>\
            <th class="col-md-1">Номер стола</th>\
            <th class="col-md-5">Дата назначения</th>\
            <th class="col-md-5">Дата отмены</th>\
            <th class="col-md-1">Примечания</th>\
        </tr>\
        </thead>\
        <tbody>\
        <tr ng-repeat="diet in diets" ng-class="{\'info\': diet.is_active}">\
            <td ng-show="!diet.deleted" ng-class="{\'has-error\': modalForm[\'diet\' + $index].$invalid}">\
                <rb-select id="diet[[$index]]" name="diet[[$index]]" ref-book="rbDiet"\
                    ng-model="diet.diet" ng-required="!diet.deleted"></rb-select>\
            </td>\
            <td ng-show="!diet.deleted">\
                <wm-datetime-as id="setDate[[$index]]" name="setDate[[$index]]" ng-model="diet.setDate" \
                    ng-required="!diet.deleted" ng-change="setDate_change(diet)" set-current-time="true" ></wm-datetime-as>\
            </td>\
            <td ng-show="!diet.deleted" ng-class="{\'has-error\': modalForm[\'endDate\' + $index].$invalid}">\
                <wm-datetime-as id="endDate[[$index]]" name="endDate[[$index]]" ng-model="diet.endDate" \
                min-date="diet.setDate" ng-change="endDate_change(diet)" set-current-time="true"></wm-datetime-as>\
            </td>\
            <td ng-show="!diet.deleted">\
                <input id="notes[[$index]]" class="form-control" type="text" ng-model="diet.notes" />\
            </td>\
            <td ng-show="!diet.deleted">\
                <button class="btn btn-danger" ng-click="remove(diet)"><i class="glyphicon glyphicon-trash"></i></button>\
            </td>\
            <td ng-show="diet.deleted" colspan="5" class="text-center"><a ng-click="restore(diet)">Восстановить</a></td>\
        </tr>\
        <tr>\
            <td colspan="5"><div class="pull-right"><button class="btn btn-success" ng-click="addModel()">Добавить</button></div></td>\
        </tr>\
        </tbody>\
    </table>\
    </ng-form>\
</div>\
<div class="modal-footer">\
    <button class="btn btn-success" ng-disabled="modalForm.$invalid || invalid_dates" ng-click="saveAndClose()">Сохранить</button>\
    <button class="btn btn-default" ng-click="$dismiss()">Отменить</button>\
</div>'
    )
}]);


var DietModalCtrl = function ($scope, $q, $modalInstance, WebMisApi, $timeout, event) {
    $scope.diets = _.deepCopy(event.diets);
    $scope.invalid_dates = false;
    $scope.addModel = function () {
        var setDate = getLatestEndDate();
        setDate = setDate === null ? moment() : moment(setDate).add(1, 'minutes');
        var model = {
            diet: null,
            setDate: setDate,
            endDate: null,
            notes: '',
            deleted: 0,
            is_active: false
        };
        $scope.diets.push(model);
        refresh_diets();
    };
    $scope.remove = function (p) {
        p.$invalid = false;
        p.deleted = 1;
        refresh_diets();
    };
    $scope.restore = function (p) {
        p.deleted = 0;
        refresh_diets();
    };
    $scope.saveAndClose = function () {
        var saveDietsList = [],
            deleteDietsIdList = [];
        $scope.diets.forEach(function (diet) {
            if(diet.deleted) {
                deleteDietsIdList.push(diet.id)
            } else {
                saveDietsList.push(diet)
            }
        });
        $q.all([
            WebMisApi.client.diet.save_list({
                client_id: event.info.client_id,
                diets_list: saveDietsList
            }),
            WebMisApi.client.diet.delete_list({diets_id_list: deleteDietsIdList})
        ]).then(function (results) {
            return WebMisApi.event.get_diets_list(event.info.id);
        }).then(function (diets) {
            $scope.$close(diets)
        });
    };
    $scope.setDate_change = function (diet) {
        if(diet.setDate) {
            setEndDate(diet);
        }
        // $timeout - для того чтобы успела отработать setEndDate
        $timeout(function () {
            refresh_diets();
        }, 500);
    };
    $scope.endDate_change = function (diet) {
        refresh_diets();
    };
    function getLatestEndDate() {
        var latestEndDate = null;
        $scope.diets.forEach(function (diet) {
            var endDate = moment(diet.endDate);
            if(!diet.deleted && endDate > latestEndDate) {
                latestEndDate = endDate;
            }
        });
        return latestEndDate;
    }
    function setEndDate(diet) {
        $timeout(function () {
            // $timeout - для того чтобы успело установиться время у endDate
                var endDate = moment(diet.setDate).subtract(1, 'minutes');
                $scope.diets.forEach(function (item) {
                    if(!item.deleted && item !== diet && !item.endDate) {
                        item.endDate = endDate;
                        // $timeout - для того чтобы успело пройти присвоение item.endDate
                        $timeout(function () {
                            item.endDate = endDate;
                        }, 0);
                    }
                });
            },
        0);
    }
    function validate_diet_dates() {
        var BreakException = {};
        try {
            $scope.diets.forEach(function (i) {
                $scope.diets.forEach(function (n) {
                    if(!i.deleted && !n.deleted && i!==n)
                    {
                        var iRange = moment.range(i.setDate, i.endDate),
                            nRange = moment.range(n.setDate, n.endDate);
                        if(iRange.overlaps(nRange, { adjacent: true })) {
                            $scope.invalid_dates = true;
                            throw BreakException;
                        }
                    }
                })
            });
            $scope.invalid_dates = false;
        } catch (e) {
            if (e !== BreakException) throw e;
        }
    }
    function recalculate_is_active() {
        $scope.diets.forEach(function (diet) {
            if(diet.deleted) {
                diet.is_active = false;
            } else {
                diet.is_active = moment.range(diet.setDate, diet.endDate).contains(moment())
            }
        });
    }
    function refresh_diets() {
        validate_diet_dates();
        recalculate_is_active();
    }

    if (!$scope.diets || $scope.diets.length===0) {
        $scope.addModel();
    }
    validate_diet_dates();
};

WebMis20.controller('DietModalCtrl', ['$scope', '$q', '$modalInstance', 'WebMisApi', '$timeout', DietModalCtrl]);
