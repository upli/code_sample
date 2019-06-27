
def get_hosp_length_list(event_id_list):
    model_provider = ApplicationModelProvider
    Action = model_provider.get('Action')
    ActionType = model_provider.get('ActionType')
    ActionProperty = model_provider.get('ActionProperty')
    ActionPropertyType = model_provider.get('ActionPropertyType')
    ActionProperty_OrgStructure = model_provider.get('ActionProperty_OrgStructure')

    EarliestAction = aliased(Action, name='EarliestAction')
    LatestAction = aliased(Action, name='LatestAction')
    q_earliest_moving = db.session.query(Action.id.label('action_id')).join(
        ActionType
    ).filter(
        Action.event_id == Event.id,
        ActionType.flatCode == STATIONARY_MOVING_CODE,
        Action.deleted == 0
    ).order_by(
        Action.begDate.asc()
    ).limit(1)

    q_latest_moving = db.session.query(Action.id.label('action_id')).join(
        ActionType
    ).filter(
        Action.event_id == Event.id,
        ActionType.flatCode == STATIONARY_MOVING_CODE,
        Action.deleted == 0
    ).order_by(
        Action.begDate.desc()
    ).limit(1)

    q_os_moving_transfer_sq = db.session.query(ActionProperty.id) \
        .join(ActionPropertyType) \
        .filter(ActionProperty.deleted == 0, ActionPropertyType.deleted == 0,
                ActionPropertyType.code == STATIONARY_ORG_STRUCT_TRANSFER_CODE,
                ActionProperty.action_id == LatestAction.id) \
        .limit(1)

    query = db.session.query(Event).join(
        EventType, rbRequestType
    ).outerjoin(
        EarliestAction, EarliestAction.id == q_earliest_moving
    ).outerjoin(
        LatestAction, LatestAction.id == q_latest_moving
    ).outerjoin(
        ActionProperty_OrgStructure, ActionProperty_OrgStructure.id == q_os_moving_transfer_sq
    ).filter(
        Event.id.in_(event_id_list)
    ).with_entities(
        Event.id,

        func.coalesce(
            EarliestAction.begDate,
            Event.setDate,
            func.curdate()
        ).label('start_date'),

        func.coalesce(
            func.IF(and_(LatestAction.id.isnot(None),
                         LatestAction.status == ActionStatus.finished[0],
                         ActionProperty_OrgStructure.value_.is_(None)),
                    LatestAction.endDate,
                    None),
            func.curdate()
        ).label('end_date'),

        func.IF(rbRequestType.code == DAY_HOSPITAL_CODE, 1, 0).label('is_day_hosp')
    )

    result = {}
    for event_id, start_date, end_date, is_day_hosp in query.all():
        if bool(is_day_hosp):
            hosp_len = (Settings.date_for_hospital_day(end_date) -
                        Settings.date_for_hospital_day(start_date)).days + 1
        else:
            hosp_len = (end_date.date() - start_date.date()).days
        result[event_id] = hosp_len

    return result
