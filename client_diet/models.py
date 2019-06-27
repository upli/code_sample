class ClientDietValidationException(Exception):
    pass


class ClientDiet(db.Model):
    __tablename__ = 'ClientDiet'

    id = db.Column(db.Integer, primary_key=True)
    createDatetime = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now)
    createPerson_id = db.Column(db.Integer, index=True, default=safe_current_user_id)
    modifyDatetime = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now,
                               onupdate=datetime.datetime.now)
    modifyPerson_id = db.Column(db.Integer, index=True, default=safe_current_user_id, onupdate=safe_current_user_id)
    deleted = db.Column(db.Integer, nullable=False, server_default=u"'0'", default=0)
    event_id = db.Column(db.ForeignKey('Event.id'), nullable=False)
    diet_id = db.Column(db.ForeignKey('rbDiet.id'), nullable=False)
    client_id = db.Column(db.ForeignKey('Client.id'), nullable=False, index=True)
    person_id = db.Column(db.Integer, db.ForeignKey('Person.id'), index=True, default=safe_current_user_id,
                          onupdate=safe_current_user_id)
    setDate = db.Column(db.Date, nullable=True, default=None)
    endDate = db.Column(db.Date, nullable=True, default=None)
    notes = db.Column(db.Text, nullable=False, default='')
    version = db.Column(db.Integer, nullable=False, default=0)

    event = db.relationship(u'Event')
    diet = db.relationship(u'rbDiet')
    person = db.relationship(u'Person')

    def __init__(self, client_id=None, diet_id=None, setDate=None, endDate=None, notes=None, deleted=None):
        self.client_id = client_id
        self.diet_id = diet_id
        self.setDate = setDate
        self.endDate = endDate
        self.notes = notes
        self.deleted = deleted

    @classmethod
    def get_or_create(cls, client_diet_id=None):
        if client_diet_id is None:
            return cls()
        else:
            return cls.query.get(safe_int(client_diet_id))

    @classmethod
    def delete_by_ids(cls, diets_id_list):
        if diets_id_list:
            cls.query.filter(cls.id.in_(diets_id_list)).update({cls.deleted: 1}, synchronize_session=False)

    def validate_relation(self, _id, Model):
        if _id is None:
            raise ClientDietValidationException(u'Не задан id для {0}'.format(Model.__name__))
        elif not db.session.query(exists().where(Model.id == _id)).scalar():
            raise ClientDietValidationException(u'{0}.id = {1} не существует'.format(Model.__name__, _id))

    def validate(self, event_id, client_id, diet_id):
        from .event import Event
        self.validate_relation(event_id, Event)
        self.validate_relation(client_id, Client)
        self.validate_relation(diet_id, rbDiet)

    def update_data(self, event_id, client_id, data):
        diet_id = safe_traverse(data, 'diet', 'id')
        self.validate(event_id, client_id, diet_id)

        self.event_id = event_id
        self.client_id = client_id
        self.diet_id = diet_id
        self.setDate = safe_date(data.get('setDate'))
        self.endDate = safe_date(data.get('endDate'))
        self.notes = data.get('notes', '')
        self.deleted = data.get('deleted', 0)

    def __json__(self):
        return {
            'id': self.id,
            'deleted': self.deleted,
            'diet': self.diet,
            'setDate': self.setDate,
            'endDate': self.endDate,
            'notes': self.notes
        }

    def __unicode__(self):
        return self.id

    def __int__(self):
        return self.id


