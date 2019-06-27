# -*- coding: utf-8 -*-

from sqlalchemy import or_, and_, func
from sqlalchemy.orm import aliased, contains_eager, joinedload, \
    Load, lazyload

from hippocrates.blueprints.event.lib.utils import get_hb_days_for_moving_list
from nemesis.lib.data import get_action_type_id, get_hosp_length_list
from hippocrates.blueprints.patients.lib.utils import get_latest_client_diet
from nemesis.lib.utils import safe_bool, safe_int, safe_traverse
from nemesis.lib.const import STATIONARY_EVENT_CODES, STATIONARY_MOVING_CODE, \
    STATIONARY_RECEIVED_CODE, STATIONARY_ORG_STRUCT_STAY_CODE, \
    STATIONARY_ORG_STRUCT_TRANSFER_CODE, STATIONARY_HOSP_BED_CODE, \
    STATIONARY_LEAVED_CODE, QUALITY_CONTROL_CODE
from nemesis.models.enums import HospStateStatus, ActionStatus, ATClass
from nemesis.lib.data_ctrl.base import BaseSelecter, BaseModelController
from nemesis.lib.diagnosis import get_events_diagnoses, format_diagnoses
from nemesis.lib.utils import initialize_name
from nemesis.lib.user import UserUtils


class HospitalizationController(BaseModelController):
    @classmethod
    def get_selecter(cls):
        return HospitalizationSelector()

    def get_hosps(self, start_dt, end_dt, history, **kwargs):
        sel = HospitalizationSelector()
        hosps_data = sel.get_latest_hosps(start_dt, end_dt, history, **kwargs)

        event_id_list = [hosp.Event.id for hosp in hosps_data.items]
        diag_data = get_events_diagnoses(event_id_list)
        diag_data = format_diagnoses(diag_data)

        moving_ids = [hosp.LatestMovingAction.id for hosp in hosps_data.items
            if hosp.LatestMovingAction]
        hb_days_data = get_hb_days_for_moving_list(moving_ids)

        latest_diets = get_latest_client_diet(event_id_list)

        hosp_list = []
        for hosp in hosps_data.items:
            event = hosp.Event
            moving = hosp.LatestMovingAction
            received = hosp.ReceivedAction
            h = {
                'id': event.id,
                'external_id': event.externalId,
                'exec_person': {
                    'id': event.execPerson_id,
                    'short_name': event.execPerson.shortNameText if event.execPerson else ''
                },
                'client': {
                    'id': event.client.id,
                    'full_name': event.client.nameText,
                    'birth_date': event.client.birthDate,
                    'age': event.client.age
                },
                'moving': {
                    'id': moving.id if moving else None,
                    'end_date': moving.endDate if moving else None,
                    'access': {
                        'can_edit': UserUtils.can_edit_action(moving),
                        'can_create': UserUtils.can_create_action(event, None, ATClass.movings[0])
                    }
                },
                'received': {
                    'id': received.id if received else None,
                    'access': {
                        'can_edit': UserUtils.can_edit_action(received)
                    }
                },
                'move_date': moving.begDate if moving else (received.begDate if received else None),
                'org_struct_name': hosp.os_name,
                'hosp_bed_name': hosp.hosp_bed_name,
                'diagnoses': diag_data.get(event.id),
                'hb_days': safe_traverse(hb_days_data, event.id, 'hb_days'),
                'diet': latest_diets.get(event.id),
            }
            hosp_list.append(h)
        return {
            'items': hosp_list,
            'count': hosps_data.total,
            'total_pages': hosps_data.pages
        }

    def get_hosps_stats(self, start_dt, end_dt, history, **kwargs):
        sel = HospitalizationSelector()
        stats1 = sel.get_hosps_status_counts(start_dt, end_dt, history, **kwargs)
        stats2 = sel.get_hosps_status_counts(start_dt, start_dt, True,
                                             statuses=[HospStateStatus.current[0]], **kwargs)
        stats3 = sel.get_hosps_by_doctor_counts(start_dt, end_dt, history, **kwargs)
        by_doctors = dict(
            (person.id if person else None,
             {
                 'person_name': person.shortNameText if person else u'Лечащий врач не назначен',
                 'events_count': cnt or 0
             })
            for person, cnt in stats3
        )
        stats4 = sel.get_hosps_without_doctor(start_dt, end_dt, history, **kwargs)
        without_doctors = dict(
            (event_id,
             {
                 'client_id': client_id,
                 'client_name': initialize_name(last_name, first_name, patr_name)
             })
            for event_id, client_id, first_name, last_name, patr_name in stats4
        )
        return {
            'count_current': stats1.count_current or 0,
            'count_received': stats1.count_received or 0,
            'count_transferred': stats1.count_transferred or 0,
            'count_leaved': stats1.count_leaved or 0,
            'count_current_prev_day': stats2.count_current or 0,
            'count_current_by_doctor': by_doctors,
            'without_doctors': without_doctors
        }

    def get_event_archive(self, **kwargs):
        """Возвращает сериализованные данные для формы Контроля качества"""
        hosps_data = self.get_event_archive_data(**kwargs)

        return {
            'items': self._visualize_archive_items(hosps_data),
            'count': hosps_data.total,
            'total_pages': hosps_data.pages
        }

    def get_event_archive_data(self, **kwargs):
        """Возвращает данные по госпитализациям, архивам и документу 'Контроль качества'"""
        sel = self.get_selecter()
        archive_data = sel.get_archive_list(**kwargs)

        return archive_data

    @staticmethod
    def _visualize_archive_items(hosps_data):
        event_ids = [hosp.Event.id for hosp in hosps_data.items]
        hb_days_data = get_hosp_length_list(event_ids)

        quality_control_type_id = get_action_type_id(QUALITY_CONTROL_CODE)

        hosp_list = []
        for hosp in hosps_data.items:
            h = {
                'id': hosp.Event.id,
                'external_id': hosp.Event.externalId,
                'set_date': hosp.Event.setDate,
                'exec_date': hosp.Event.execDate,
                'client': {
                    'id': hosp.Event.client.id,
                    'full_name': hosp.Event.client.nameText,
                    'birth_date': hosp.Event.client.birthDate,
                    'age': hosp.Event.client.age
                },
                'org_struct_name': hosp.os_name,
                'hb_days': hb_days_data.get(hosp.Event.id),
                'event_archive': {
                    'id': hosp.archive_id,
                    'archive': hosp.archive,
                },
                'quality_control': {
                    'id': getattr(hosp.QualityControlAction, 'id', None),
                    'status': ActionStatus(getattr(hosp.QualityControlAction, 'status', None)),
                    'actionType_id': getattr(hosp.QualityControlAction, 'actionType_id', quality_control_type_id),
                }
            }
            hosp_list.append(h)

        return hosp_list


class HospitalizationSelector(BaseSelecter):

    def __init__(self, query=None):
        Action = self.model_provider.get('Action')
        OrgStructure = self.model_provider.get('OrgStructure')
        OrgStructure_HospitalBed = self.model_provider.get('OrgStructure_HospitalBed')

        self.BaseEvent = self.model_provider.get('Event')
        self.BaseEvent_execDate = self._get_col_raw(self.BaseEvent, 'execDate')
        self.BaseClient = self.model_provider.get('Client')
        self.EventArchive = self.model_provider.get('EventArchive')
        self.MovingAction = aliased(Action, name='LatestMovingAction')
        self.MovingAction_begDate = self._get_col_raw(self.MovingAction, 'begDate')
        self.MovingAction_endDate = self._get_col_raw(self.MovingAction, 'endDate')
        self.ReceivedAction = aliased(Action, name='ReceivedAction')
        self.ReceivedAction_begDate = self._get_col_raw(self.ReceivedAction, 'begDate')
        self.ReceivedAction_endDate = self._get_col_raw(self.ReceivedAction, 'endDate')
        self.LeavedAction = aliased(Action, name='LeavedAction')
        self.QualityControlAction = aliased(Action, name='QualityControlAction')
        self.LocationOSfromMoving = aliased(OrgStructure, name='LocationOrgStructFromMoving')
        self.LocationOSfromReceived = aliased(OrgStructure, name='LocationOrgStructFromReceived')
        self.MovingOSHB = aliased(OrgStructure_HospitalBed, name='MovingHospitalBed')
        self.MovingOrgStructTransfer = aliased(OrgStructure, name='MovingOrgStructTransfer')
        self.q_movings_transfered_through = None

        self.start_dt = None
        self.end_dt = None
        self.hosp_status = None
        self.flt_org_struct_id = None
        self.flt_client_id = None
        self.flt_exec_person_id = None
        self.flt_external_id = None
        self.flt_not_in_archive = None
        self.flt_closed_only = None
        self.history = None
        self._latest_location_joined = False
        self._location_os_joined = False
        self._leaved_joined = False
        self._hosp_bed_joined = False
        self._moving_os_transfer_joined = False
        self._moving_transfer_through_joined = False
        super(HospitalizationSelector, self).__init__(query)

    def set_base_query(self):
        EventType = self.model_provider.get('EventType')
        rbRequestType = self.model_provider.get('rbRequestType')

        self.query = self.session.query(self.BaseEvent).join(
            self.BaseClient, EventType, rbRequestType
        ).filter(
            self.BaseEvent.deleted == 0,
            rbRequestType.code.in_(STATIONARY_EVENT_CODES),
        )
        if not self.start_dt:
            self.query = self.query.filter(self.BaseEvent_execDate.is_(None))
        else:
            self.query = self.query.filter(
                or_(self.BaseEvent_execDate.is_(None),
                    self.BaseEvent_execDate >= self.start_dt)
            )
        if self.flt_client_id is not None:
            self.query = self.query.filter(self.BaseClient.id == self.flt_client_id)
        if self.flt_exec_person_id is not None:
            self.query = self.query.filter(self.BaseEvent.execPerson_id == self.flt_exec_person_id)
        if self.flt_external_id is not None:
            self.query = self.query.filter(
                self.BaseEvent.externalId.like(u'%{0}%'.format(self.flt_external_id))
            )
        if self.flt_not_in_archive:
            self.query = self.query.filter(
                or_(
                    self.EventArchive.archive == 0,
                    self.EventArchive.archive.is_(None)
                )
            )
        if self.flt_closed_only:
            self.query = self.query.filter(self.BaseEvent_execDate.isnot(None))

        self._latest_location_joined = False
        self._location_os_joined = False
        self._leaved_joined = False
        self._hosp_bed_joined = False
        self._moving_os_transfer_joined = False
        self.q_movings_transfered_through = None
        self._moving_transfer_through_joined = False

    def get_latest_hosps(self, start_dt, end_dt, history, **kwargs):
        self.start_dt = start_dt
        self.end_dt = end_dt
        self.history = history
        self.hosp_status = safe_int(kwargs.get('hosp_status'))
        self.flt_org_struct_id = safe_int(kwargs.get('org_struct_id'))
        self.flt_client_id = safe_int(kwargs.get('client_id'))
        self.flt_exec_person_id = safe_int(kwargs.get('exec_person_id'))
        self.flt_external_id = kwargs.get('external_id')

        self.set_base_query()
        self._filter_by_latest_location()
        self._filter_by_status()
        self._join_location_org_structure()
        self._join_hosp_bed()

        self.query = self.query.with_entities(
            self.BaseEvent,
            self.MovingAction,
            self.ReceivedAction,
            func.IF(self.MovingAction.id.isnot(None),
                    self.LocationOSfromMoving.name,
                    self.LocationOSfromReceived.name).label('os_name'),
            self.MovingOSHB.name.label('hosp_bed_name')
        )
        self.query = self.query.order_by(
            func.IF(self.MovingAction.id.isnot(None),
                    self.MovingAction_begDate,
                    self.ReceivedAction_begDate).desc()
        )

        self.query = self.query.options(
            contains_eager(self.BaseEvent.client),
            lazyload('*'),
            joinedload(self.BaseEvent.execPerson),
            # load only attrs an action, that will be used later
            Load(self.MovingAction).load_only(
                'id', 'begDate', 'endDate', 'status', 'event_id', 'person_id', 'createPerson_id'
            ).joinedload('actionType').load_only('class_'),
            Load(self.MovingAction).contains_eager('event'),
            Load(self.ReceivedAction).load_only(
                'id', 'begDate', 'endDate', 'status', 'event_id', 'person_id', 'createPerson_id'
            ).joinedload('actionType').load_only('class_'),
            Load(self.ReceivedAction).contains_eager('event')
        )
        return self.get_paginated(kwargs)

    def get_hosps_status_counts(self, start_dt, end_dt, history, **kwargs):
        self.start_dt = start_dt
        self.end_dt = end_dt
        self.history = history
        self.hosp_status = safe_int(kwargs.get('hosp_status'))
        self.flt_org_struct_id = safe_int(kwargs.get('org_struct_id'))
        self.flt_client_id = safe_int(kwargs.get('client_id'))
        self.flt_exec_person_id = safe_int(kwargs.get('exec_person_id'))
        self.flt_external_id = kwargs.get('external_id')

        statuses = set(kwargs.get('statuses') or HospStateStatus.get_values())

        self.set_base_query()
        self._join_latest_location()
        self._join_location_org_structure()
        self._join_moving_os_transfer()
        self._join_movings_transfered_through()
        self._join_leaved()

        self.query = self.query.filter(
            or_(self.MovingAction.id.isnot(None),
                self.ReceivedAction.id.isnot(None)),
        ).with_entities()
        if HospStateStatus.current[0] in statuses:
            # кол-во текущих
            self.query = self.query.add_column(
                func.SUM(
                    func.IF(func.IF(self.MovingAction.id.isnot(None),
                                    and_(self.MovingAction_begDate < self.end_dt,
                                         or_(self.MovingAction_endDate.is_(None),
                                             self.end_dt <= self.MovingAction_endDate),
                                         func.IF(self.flt_org_struct_id is not None,
                                                 self.LocationOSfromMoving.id == self.flt_org_struct_id,
                                                 1)
                                         ),
                                    and_(self.ReceivedAction_begDate < self.end_dt,
                                         or_(self.ReceivedAction_endDate.is_(None),
                                             self.end_dt <= self.ReceivedAction_endDate),
                                         func.IF(self.flt_org_struct_id is not None,
                                                 self.LocationOSfromReceived.id == self.flt_org_struct_id,
                                                 1)
                                         )),
                            1, 0)
                ).label('count_current')
            )

        if HospStateStatus.received[0] in statuses:
            # кол-во поступивших
            self.query = self.query.add_column(
                func.SUM(
                    func.IF(func.IF(self.MovingAction.id.isnot(None),
                                    and_(self.MovingAction_begDate < self.end_dt,
                                         self.start_dt <= self.MovingAction_begDate,
                                         or_(self.MovingAction_endDate.is_(None),
                                             self.start_dt <= self.MovingAction_endDate),
                                         func.IF(self.flt_org_struct_id is not None,
                                                 self.LocationOSfromMoving.id == self.flt_org_struct_id,
                                                 1)
                                         ),
                                    and_(self.ReceivedAction_begDate < self.end_dt,
                                         self.start_dt <= self.ReceivedAction_begDate,
                                         or_(self.ReceivedAction_endDate.is_(None),
                                             self.start_dt <= self.ReceivedAction_endDate),
                                         func.IF(self.flt_org_struct_id is not None,
                                                 self.LocationOSfromReceived.id == self.flt_org_struct_id,
                                                 1)
                                         )
                                    ),
                            1, 0)
                ).label('count_received')
            )

        if HospStateStatus.transferred[0] in statuses:
            # кол-во переведенных
            self.query = self.query.add_column(
                func.SUM(
                    func.IF(self.q_movings_transfered_through.c.event_id.isnot(None),
                            1, 0)
                ).label('count_transferred')
            )

        if HospStateStatus.leaved[0] in statuses:
            # кол-во выписанных
            self.query = self.query.add_column(
                func.SUM(
                    func.IF(and_(self.LeavedAction.id.isnot(None),
                                 self.MovingOrgStructTransfer.id.is_(None),
                                 self.MovingAction_begDate < self.end_dt,
                                 self.MovingAction_endDate >= self.start_dt,
                                 self.MovingAction_endDate < self.end_dt),
                            1, 0)
                ).label('count_leaved')
            )

        return self.get_one()

    def get_hosps_by_doctor_counts(self, start_dt, end_dt, history, **kwargs):
        self.start_dt = start_dt
        self.end_dt = end_dt
        self.history = history
        self.hosp_status = HospStateStatus.current[0]
        self.flt_org_struct_id = safe_int(kwargs.get('org_struct_id'))

        self.set_base_query()
        self._join_latest_location()
        self._filter_by_status()

        Person = self.model_provider.get('Person')

        self.query = self.query.join(
            Person, self.BaseEvent.execPerson_id == Person.id
        ).group_by(
            self.BaseEvent.execPerson_id
        ).with_entities(
            Person,
            func.count(self.BaseEvent.id.distinct()).label('count_events')
        )

        return self.get_all()

    def get_hosps_without_doctor(self, start_dt, end_dt, history, **kwargs):
        self.start_dt = start_dt
        self.end_dt = end_dt
        self.history = history
        self.hosp_status = HospStateStatus.current[0]
        self.flt_org_struct_id = safe_int(kwargs.get('org_struct_id'))

        self.set_base_query()
        self._join_latest_location()
        self._filter_by_status()

        self.query = self.query.filter(
            self.BaseEvent.execPerson_id.is_(None)
        ).with_entities(
            self.BaseEvent.id.distinct().label('event_id'),
            self.BaseClient.id.label('client_id'),
            self.BaseClient.firstName.label('first_name'),
            self.BaseClient.lastName.label('last_name'),
            self.BaseClient.patrName.label('patr_name'),
        )

        return self.get_all()

    def get_archive_list(self, **kwargs):
        self.start_dt = kwargs.get('start_dt')
        self.end_dt = kwargs.get('end_dt')
        self.flt_client_id = safe_int(kwargs.get('client_id'))
        self.flt_external_id = kwargs.get('external_id')
        self.flt_not_in_archive = safe_bool(kwargs.get('not_in_archive'))
        self.flt_closed_only = True

        self.set_base_query()
        self._join_latest_location()
        self._join_location_org_structure()
        self._join_event_archive()
        self._join_quality_control()

        self.query = self.query.with_entities(
            self.BaseEvent,
            func.IF(self.MovingAction.id.isnot(None),
                    self.LocationOSfromMoving.shortName,
                    self.LocationOSfromReceived.shortName).label('os_name'),
            self.EventArchive.id.label('archive_id'),
            self.EventArchive.archive.label('archive'),
            self.QualityControlAction
        ).order_by(
            func.IF(self.MovingAction.id.isnot(None),
                    self.MovingAction_begDate,
                    self.ReceivedAction_begDate).desc()
        ).options(
            contains_eager(self.BaseEvent.client),
        )
        return self.get_paginated(kwargs)

    def _filter_by_latest_location(self):
        self._join_latest_location()
        if not self.history:
            self.query = self.query.filter(
                func.IF(self.MovingAction.id.isnot(None),
                        # движение попадает во временной интервал
                        and_(self.MovingAction_begDate < self.end_dt,
                             or_(self.MovingAction_endDate.is_(None),
                                 self.start_dt <= self.MovingAction_endDate)
                             ),
                        # поступление попадает во временной интервал
                        and_(self.ReceivedAction_begDate < self.end_dt,
                             or_(self.ReceivedAction_endDate.is_(None),
                                 self.start_dt <= self.ReceivedAction_endDate)
                             )
                        )
            )

    def _filter_by_status(self):
        if self.hosp_status == HospStateStatus.transferred[0]:
            # Переведенные - Action.endDate между beg_date и end_date, а поле "Переведен в отделение"
            # не пустое, отделение пребывания равно текущему отделению пользователя.
            self._join_movings_transfered_through()
            self.query = self.query.filter(
                self.q_movings_transfered_through.c.event_id.isnot(None)
            )
        else:
            self.query = self.query.filter(
                or_(self.MovingAction.id.isnot(None),
                    self.ReceivedAction.id.isnot(None)),
            )
            self._filter_by_location_os()

            # Текущие - Action.endDate для движения пусто или больше end_date,
            # отделение пребывания равно текущему отделению пользователя. Плюс отображаем пациентов,
            # у которых есть поступление в это отделение, но их еще не разместили на койке
            if self.hosp_status == HospStateStatus.current[0]:
                self.query = self.query.filter(
                    func.IF(self.MovingAction.id.isnot(None),
                            or_(self.MovingAction_endDate.is_(None),
                                self.MovingAction_endDate >= self.end_dt),
                            or_(self.ReceivedAction_endDate.is_(None),
                                self.ReceivedAction_endDate >= self.end_dt)
                            )
                )
            # Поступившие - Action.begDate для движения (или поступления) более или равно beg_date,
            # а endDate любая, отделение пребывания равно текущему отделению пользователя.
            elif self.hosp_status == HospStateStatus.received[0]:
                self.query = self.query.filter(
                    func.IF(self.MovingAction.id.isnot(None),
                            and_(self.MovingAction_begDate >= self.start_dt,
                                 self.MovingAction_begDate < self.end_dt),
                            and_(self.ReceivedAction_begDate >= self.start_dt,
                                 self.ReceivedAction_begDate < self.end_dt),
                            )
                )
            # Выписанные - Action.endDate между beg_date и end_date, а поле "Переведен в отделение"
            # пусто. Также должен присутствовать "Выписной эпикриз".
            elif self.hosp_status == HospStateStatus.leaved[0]:
                self._join_leaved()
                self._join_moving_os_transfer()

                self.query = self.query.filter(
                    self.LeavedAction.id.isnot(None),
                    self.MovingOrgStructTransfer.id.is_(None),
                    and_(self.MovingAction_endDate >= self.start_dt,
                         self.MovingAction_endDate < self.end_dt)
                )

    def _join_latest_location(self):
        if self._latest_location_joined:
            return

        Action = self.model_provider.get('Action')
        Action_begDate = self._get_col_raw(Action, 'begDate')
        Action_endDate = self._get_col_raw(Action, 'endDate')
        ActionType = self.model_provider.get('ActionType')

        q_latest_moving = self.session.query(Action.id.label('action_id')).join(
            ActionType
        ).filter(
            Action.event_id == self.BaseEvent.id,
            ActionType.flatCode == STATIONARY_MOVING_CODE,
            Action.deleted == 0
        ).order_by(
            Action_begDate.desc()
        )
        if self.history:
            # движение попадает во временной интервал
            q_latest_moving = q_latest_moving.filter(
                Action_begDate < self.end_dt,
                or_(Action_endDate.is_(None),
                    Action_endDate >= self.start_dt)
            )
        q_latest_moving = q_latest_moving.limit(1)

        q_received = self.session.query(Action.id.label('action_id')).join(
            ActionType
        ).filter(
            Action.event_id == self.BaseEvent.id,
            ActionType.flatCode == STATIONARY_RECEIVED_CODE,
            Action.deleted == 0
        ).order_by(
            Action_begDate.desc()
        )
        if self.history:
            # поступление попадает во временной интервал
            q_received = q_received.filter(
                Action_begDate < self.end_dt,
                or_(Action_endDate.is_(None),
                    Action_endDate >= self.start_dt)
            )
        q_received = q_received.limit(1)

        self.query = self.query.outerjoin(
            self.MovingAction, self.MovingAction.id == q_latest_moving
        ).outerjoin(
            self.ReceivedAction, self.ReceivedAction.id == q_received
        )
        self._latest_location_joined = True

    def _join_location_org_structure(self):
        if self._location_os_joined:
            return

        ActionProperty = self.model_provider.get('ActionProperty')
        ActionPropertyType = self.model_provider.get('ActionPropertyType')
        ActionProperty_OrgStructure = self.model_provider.get('ActionProperty_OrgStructure')
        AP_OS_Moving = aliased(ActionProperty_OrgStructure, name='AP_OS_Moving')
        AP_OS_Received = aliased(ActionProperty_OrgStructure, name='AP_OS_Received')

        q_os_stay_sq = self.session.query(ActionProperty.id)\
            .join(ActionPropertyType)\
            .filter(ActionProperty.deleted == 0, ActionPropertyType.deleted == 0,
                    ActionPropertyType.code == STATIONARY_ORG_STRUCT_STAY_CODE,
                    ActionProperty.action_id == self.MovingAction.id)\
            .limit(1)
        q_os_transfer_sq = self.session.query(ActionProperty.id)\
            .join(ActionPropertyType)\
            .filter(ActionProperty.deleted == 0, ActionPropertyType.deleted == 0,
                    ActionPropertyType.code == STATIONARY_ORG_STRUCT_TRANSFER_CODE,
                    ActionProperty.action_id == self.ReceivedAction.id)\
            .limit(1)

        self.query = self.query.outerjoin(
            AP_OS_Moving, AP_OS_Moving.id == q_os_stay_sq
        ).outerjoin(
            self.LocationOSfromMoving, self.LocationOSfromMoving.id == AP_OS_Moving.value_
        ).outerjoin(
            AP_OS_Received, AP_OS_Received.id == q_os_transfer_sq
        ).outerjoin(
            self.LocationOSfromReceived, self.LocationOSfromReceived.id == AP_OS_Received.value_
        )
        self._location_os_joined = True

    def _filter_by_location_os(self):
        if self.flt_org_struct_id is not None:
            self._join_location_org_structure()
            self.query = self.query.filter(
                func.IF(self.MovingAction.id.isnot(None),
                        self.LocationOSfromMoving.id == self.flt_org_struct_id,
                        self.LocationOSfromReceived.id == self.flt_org_struct_id)
            )

    def _join_hosp_bed(self):
        if self._hosp_bed_joined:
            return

        ActionProperty = self.model_provider.get('ActionProperty')
        ActionPropertyType = self.model_provider.get('ActionPropertyType')
        ActionProperty_HospitalBed = self.model_provider.get('ActionProperty_HospitalBed')

        q_hosp_bed_sq = self.session.query(ActionProperty.id.label('ap_id'))\
            .join(ActionPropertyType)\
            .filter(ActionProperty.deleted == 0, ActionPropertyType.deleted == 0,
                    ActionPropertyType.code == STATIONARY_HOSP_BED_CODE,
                    ActionProperty.action_id == self.MovingAction.id)\
            .limit(1)

        self.query = self.query.outerjoin(
            ActionProperty_HospitalBed, ActionProperty_HospitalBed.id == q_hosp_bed_sq
        ).outerjoin(
            self.MovingOSHB, self.MovingOSHB.id == ActionProperty_HospitalBed.value_
        )

        self._hosp_bed_joined = True

    def _join_leaved(self):
        if self._leaved_joined:
            return

        Action = self.model_provider.get('Action')
        Action_begDate = self._get_col_raw(Action, 'begDate')
        Action_endDate = self._get_col_raw(Action, 'endDate')
        ActionType = self.model_provider.get('ActionType')

        q_leaved = self.session.query(Action.id.label('action_id')).join(
            ActionType
        ).filter(
            Action.event_id == self.BaseEvent.id,
            ActionType.flatCode == STATIONARY_LEAVED_CODE,
            Action.deleted == 0
        ).order_by(
            Action_begDate.desc()
        )
        if self.history:
            # выписка попадает во временной интервал
            q_leaved = q_leaved.filter(
                Action_begDate < self.end_dt,
                or_(Action_endDate.is_(None),
                    Action_endDate >= self.start_dt)
            )
        q_leaved = q_leaved.limit(1)

        self.query = self.query.outerjoin(
            self.LeavedAction, self.LeavedAction.id == q_leaved
        )
        self._leaved_joined = True

    def _join_moving_os_transfer(self):
        if self._moving_os_transfer_joined:
            return

        ActionProperty = self.model_provider.get('ActionProperty')
        ActionPropertyType = self.model_provider.get('ActionPropertyType')
        ActionProperty_OrgStructure = self.model_provider.get('ActionProperty_OrgStructure')
        AP_OS_Moving_Transfer = aliased(ActionProperty_OrgStructure, name='AP_OS_Moving_Transfer')

        q_os_moving_transfer_sq = self.session.query(ActionProperty.id) \
            .join(ActionPropertyType) \
            .filter(ActionProperty.deleted == 0, ActionPropertyType.deleted == 0,
                    ActionPropertyType.code == STATIONARY_ORG_STRUCT_TRANSFER_CODE,
                    ActionProperty.action_id == self.MovingAction.id) \
            .limit(1)

        self.query = self.query.outerjoin(
            AP_OS_Moving_Transfer, AP_OS_Moving_Transfer.id == q_os_moving_transfer_sq
        ).outerjoin(
            self.MovingOrgStructTransfer, self.MovingOrgStructTransfer.id == AP_OS_Moving_Transfer.value_
        )
        self._moving_os_transfer_joined = True

    def _join_movings_transfered_through(self):
        if self._moving_transfer_through_joined:
            return

        Action = self.model_provider.get('Action')
        ActionThrough = aliased(Action, name='ActionThrough')
        ActionThrough_begDate = self._get_col_raw(ActionThrough, 'begDate')
        ActionThrough_endDate = self._get_col_raw(ActionThrough, 'endDate')
        ActionType = self.model_provider.get('ActionType')
        Event = self.model_provider.get('Event')
        EventType = self.model_provider.get('EventType')
        rbRequestType = self.model_provider.get('rbRequestType')
        ActionProperty = self.model_provider.get('ActionProperty')
        ActionPropertyType = self.model_provider.get('ActionPropertyType')
        ActionProperty_OrgStructure = self.model_provider.get('ActionProperty_OrgStructure')

        AP_OS_Moving_Transfer = aliased(ActionProperty_OrgStructure, name='AP_OS_Moving_TransferThr')
        AP_OS_Moving_Stay = aliased(ActionProperty_OrgStructure, name='AP_OS_Moving_StayThr')

        q_os_moving_stay_sq = self.session.query(ActionProperty.id) \
            .join(ActionPropertyType) \
            .filter(ActionProperty.deleted == 0, ActionPropertyType.deleted == 0,
                    ActionPropertyType.code == STATIONARY_ORG_STRUCT_STAY_CODE,
                    ActionProperty.action_id == ActionThrough.id)
        q_os_moving_stay_sq = q_os_moving_stay_sq.limit(1)

        q_os_moving_transfer_sq = self.session.query(ActionProperty.id) \
            .join(ActionPropertyType) \
            .filter(ActionProperty.deleted == 0, ActionPropertyType.deleted == 0,
                    ActionPropertyType.code == STATIONARY_ORG_STRUCT_TRANSFER_CODE,
                    ActionProperty.action_id == ActionThrough.id) \
            .limit(1)

        q_movings = self.session.query(ActionThrough).join(
            Event, EventType, rbRequestType, ActionType
        ).join(
            AP_OS_Moving_Stay, AP_OS_Moving_Stay.id == q_os_moving_stay_sq
        ).join(
            # == AP_OS_Moving_Transfer.value_.isnot(None)
            AP_OS_Moving_Transfer, AP_OS_Moving_Transfer.id == q_os_moving_transfer_sq
        ).filter(
            Event.deleted == 0, Event.execDate.is_(None),
            rbRequestType.code.in_(STATIONARY_EVENT_CODES),
            ActionType.flatCode == STATIONARY_MOVING_CODE,
            ActionThrough_begDate < self.end_dt,
            ActionThrough_endDate >= self.start_dt, ActionThrough_endDate < self.end_dt
        ).group_by(
            Event.id
        ).with_entities(
            Event.id.label('event_id'), (func.count(ActionThrough.id) > 0).label('was_transfered_through')
        )
        if self.flt_org_struct_id is not None:
            q_movings = q_movings.filter(
                AP_OS_Moving_Stay.value_ == self.flt_org_struct_id)
        q_movings = q_movings.subquery('TransferedThroughMovingsSQ')

        self.q_movings_transfered_through = q_movings

        self.query = self.query.outerjoin(
            q_movings, q_movings.c.event_id == self.BaseEvent.id
        )
        self._moving_transfer_through_joined = True

    def _join_event_archive(self):
        q_latest_event_archive = self.session.query(self.EventArchive.id.label('event_archive_id')).filter(
            self.EventArchive.event_id == self.BaseEvent.id,
        ).order_by(
            self.EventArchive.createDatetime.desc()
        ).limit(1)

        self.query = self.query\
            .outerjoin(self.EventArchive, self.EventArchive.id == q_latest_event_archive.correlate(self.BaseEvent))

    def _join_quality_control(self):
        Action = self.model_provider.get('Action')
        ActionType = self.model_provider.get('ActionType')

        q_quality_control = self.session.query(Action.id.label('action_id')).join(ActionType).filter(
            Action.event_id == self.BaseEvent.id,
            ActionType.flatCode == QUALITY_CONTROL_CODE,
            Action.deleted == 0
        ).order_by(
            Action.id.desc()
        ).limit(1)

        self.query = self.query\
            .outerjoin(self.QualityControlAction, self.QualityControlAction.id == q_quality_control)
