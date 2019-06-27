'use strict';

var EventArchiveCtrl = function ($scope, $q, WebMisApi, HospitalizationsService, SelectAll,
        PrintingService, TimeoutCallback, RefBookService) {
    $scope.filter = {
        client: null,
        external_id: null,
        start_date: null,
        end_date: null
    };
    $scope.pager = {
        current_page: 1,
        per_page: 50,
        max_pages: 10,
        pages: null,
        record_count: null
    };
    var req_type_codes = ['clinic', 'hospital'];
    $scope.rbRequestType = RefBookService.get('rbRequestType');
    $scope.hosp_list = [];
    $scope.ps_elist = new PrintingService('event_archive_list');
    $scope.selectedRecords = new SelectAll([]); // Чекбоксы колонки "Архив"
    $scope.archiveSelect = new SelectAll([]);  // Модель для фильтра "ИБ не сдана"
    $scope.reqTypeSelect = new SelectAll([]);  // Модель для фильтров видов обращений

    $scope.getEventUrl = function (event_id) {
        return WebMisApi.event.get_info_url({event_id: event_id});
    };
    $scope.getClientUrl = function (client_id) {
        return WebMisApi.client.get_html_url({client_id: client_id});
    };
    $scope.ps_elist_resolve = function () {
        var args = get_args();
        // Для вывода на печать выводим весь список без пагинации
        args['paginate'] = false;
        return args
    };
    $scope.isActionFinished = function (action) {
        return safe_traverse(action, ['status', 'code']) === 'finished';
    };
    $scope.onCheckBoxChanged = function() {
        refreshHospListPageReset();
    };
    $scope.openQualityControl = function (hosp) {
        HospitalizationsService.openQualityControl(hosp, refreshHospList);
    };
    $scope.onPageChanged = function () {
        refreshHospList();
    };
    $scope.onChangeClient = function () {
        $scope.filter.external_id = null;
        refreshHospListPageReset();
    };
    $scope.onChangeExternalId = function () {
        $scope.filter.client = null;
        tc.start();
    };
    $scope.onChangeArchiveStatus = function(event_id) {
        var is_selected = $scope.selectedRecords.selected(event_id);
        HospitalizationsService.archive.save({event_id: event_id, archive: is_selected}).then(refreshHospList);
    };

    var setDefaultFilter = function () {
        $scope.filter = {
            client: null,
            external_id: null,
            start_date: moment().subtract(7, 'd').toDate(),
            end_date: moment().toDate(),
        };
        $scope.archiveSelect.selectNone();
        $scope.reqTypeSelect.selectNone();
        $scope.reqTypeSelect.select('hospital');

    };
    var setHospListData = function (paged_data) {
        $scope.pager.record_count = paged_data.count;
        $scope.pager.pages = paged_data.total_pages;
        $scope.hosp_list = paged_data.items;
        $scope.selectedRecords.setSource(paged_data.items.map(function (hosp) {
            if (hosp.event_archive.archive) return hosp.id;
        }));
    };
    var get_args = function () {
        var flt_req_types = $scope.reqTypeSelect.selected();
        return {
            paginate: true,
            page: $scope.pager.current_page,
            per_page: $scope.pager.per_page,
            start_dt: $scope.filter.start_date,
            end_dt: $scope.filter.end_date,
            client_id: safe_traverse($scope.filter, ['client', 'id']) || undefined,
            external_id: $scope.filter.external_id || undefined,
            not_in_archive: $scope.archiveSelect.selected('filterNotInArchive'),
            request_types: flt_req_types.length ? flt_req_types : undefined
        };
    };
    var refreshHospList = function () {
        var args = get_args();
        return HospitalizationsService.archive.get_list(args).then(setHospListData);
    };
    var refreshHospListPageReset = function () {
        $scope.pager.current_page = 1;
        refreshHospList();
    };

    var tc = new TimeoutCallback(refreshHospListPageReset, 600);
    var watch_with_reload = function (n, o) {
        if (angular.equals(n, o)) return;
        tc.start();
    };
    $scope.$watch('filter.start_date', watch_with_reload);
    $scope.$watch('filter.end_date', watch_with_reload);

    $scope.init = function () {
        $q.when($scope.rbRequestType.loading, function () {
            $scope.request_types = $scope.rbRequestType.objects.filter(function (o) {
                return req_type_codes.has(o.code);
            });

            setDefaultFilter();
            tc.start();
        });
    };

    $scope.init();
};

WebMis20.controller('EventArchiveCtrl', ['$scope', '$q', 'WebMisApi', 'HospitalizationsService',
    'SelectAll', 'PrintingService', 'TimeoutCallback', 'RefBookService', EventArchiveCtrl]);
