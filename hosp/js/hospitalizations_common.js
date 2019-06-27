'use strict';

WebMis20.service('HospitalizationsService', ['WebMisApi', 'WMConfig', 'WMWindowSync',
    function (WebMisApi, WMConfig, WMWindowSync) {
        this.get_hosp_list = function (args) {
            return WebMisApi.hospitalizations.get_list(args);
        };
        this.get_hosp_list_short = function (args) {
            return WebMisApi.hospitalizations.get_list_short(args);
        };
        this.get_hosps_stats = function (args) {
            return WebMisApi.hospitalizations.get_stats(args);
        };
        this.openQualityControl = function (hosp, callback) {
            var params, url;

            if (hosp.quality_control.id) {
                params = {
                    action_id: hosp.quality_control.id
                };
            } else {
                params = {
                    action_type_id: hosp.quality_control.actionType_id,
                    event_id: hosp.id
                };
            }

            url = aux.buildUrl(WMConfig.url.actions.html.action, params);
            WMWindowSync.openTab(url, callback);
        };
        this.archive = {
            get_list: function (args) {
                return WebMisApi.hospitalizations.get_archive_list(args);
            },
            save: function (args) {
                return WebMisApi.event.save_event_archive(args);
            }
        };
    }]
);
