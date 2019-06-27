
class VMPCoupon(db.Model):
    __tablename__ = 'VMPCoupon'

    id = db.Column(db.Integer, primary_key=True)
    createDatetime = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now)
    createPerson_id = db.Column(db.ForeignKey('Person.id'), index=True, default=safe_current_user_id)
    modifyDatetime = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    modifyPerson_id = db.Column(db.ForeignKey('Person.id'), index=True, default=safe_current_user_id, onupdate=safe_current_user_id)
    deleted = db.Column(db.Integer, nullable=False, server_default=u"'0'")

    number = db.Column(db.Integer, nullable=False)
    MKB_id = db.Column(db.ForeignKey('MKB.id'), nullable=False)
    date = db.Column(db.Date)
    begDate = db.Column(db.DateTime)
    endDate = db.Column(db.DateTime)
    quotaType_id = db.Column(db.ForeignKey('QuotaType.id'), nullable=False)
    client_id = db.Column(db.ForeignKey('Client.id'), nullable=False)
    clientQuoting_id = db.Column(db.Integer)
    fileLink = db.Column('file', db.String)

    MKB_object = db.relationship('MKB')
    quotaType = db.relationship('QuotaType')

    def __init__(self, *args, **kwargs):
        super(VMPCoupon, self).__init__(*args, **kwargs)
        self._parsed = {}

    @property
    def MKB(self):
        return self.MKB_object.DiagID

    @MKB.setter
    def MKB(self, value):
        self.MKB_object = MKB.query.filter(MKB.DiagID == value).first()

    @property
    def parsed(self):
        return self._parsed

    @property
    @db_non_flushable
    def is_unique(self, ):
        return not bool(VMPCoupon.query.filter_by(number=self.number, deleted=0).count())

    @classmethod
    def from_zip(cls, zip64, finance_id=None):
        """
        Заполняем VMPCoupon из zip архива, который содержит два html файла:
            talon.xls - Талон ВМП
            card.xls - Карта пациента
        """
        from nemesis.models.client import Client

        unziped_files = unzip2dict(zip64)

        # VMP Coupon
        talon_xls = html2xls(unziped_files['talon.xls'])
        talon_book = XlsReader(file_contents=talon_xls.read())

        self = cls()
        self.number = talon_book.get_cells_by_label(u'Талон', 'D', 'EFGHIJKLMNOPQRSTU')
        self.MKB = talon_book.get_cells_by_label(u'Код диагноза по МКБ-10(ОУЗ)', 'D', 'GHIJK')

        quota_type_code = talon_book.get_cells_by_label(u'Наименование вида ВМП', 'D', 'FGHIJKLMNOPQ')
        quota_date_str = talon_book.get_cells_by_label(u'Дата принятия решения', 'D', 'FGHIJKLM')
        quota_date = safe_date(quota_date_str, '%d/%m/%y')
        self._parsed.update({
            'quota_type_code': quota_type_code,
            'quota_date': quota_date
        })

        self.quotaType = QuotaType.query.join(QuotaCatalog).filter(
            QuotaType.code == quota_type_code,
            QuotaType.deleted == 0,
            between(quota_date, QuotaCatalog.begDate, QuotaCatalog.endDate),
            QuotaCatalog.finance_id == finance_id if finance_id else True
        ).first()
        plan_hosp_date_str = talon_book.get_cells_by_label(u'Дата планируемой госпитализации',
                                                           'D', 'FGHIJKLM')
        self.date = safe_date(plan_hosp_date_str, '%d/%m/%y')
        talon_book.book.release_resources()

        # Client card
        card_xls = html2xls(unziped_files['card.xls'])
        card_book = XlsReader(file_contents=card_xls.read())

        first_name = card_book.get_cells_by_label(u'Имя', 'H', 'I').capitalize()
        last_name = card_book.get_cells_by_label(u'Фамилия', 'D', 'E').capitalize()
        patr_name = card_book.get_cells_by_label(u'Отчество', 'D', 'F').capitalize()
        document_type = card_book.get_cells_by_label(
            u'Код и вид\r\n  документа, удостоверяющего личность', 'D', 'E')
        document_number = card_book.get_cells_by_label(u'Серия и номер документа', 'D', 'E')
        birthdate_str = card_book.get_cells_by_label(u'Дата рождения', 'J', 'LMNOPQRSTU')
        birthdate = safe_date(birthdate_str, '%d/%m/%Y')
        unformatted_snils = card_book.get_cells_by_label(u'СНИЛС (при наличии)', 'D', 'FGHIJKLMNOPQRS')
        card_book.book.release_resources()

        client = None
        # Round one!
        if unformatted_snils:
            client = Client.query.filter(Client.SNILS == unformatted_snils,
                                         Client.deleted == 0).first()
        if not client:
            # Round two!
            if first_name or last_name or birthdate:
                query = Client.query.filter(
                    Client.firstName == first_name,
                    Client.lastName == last_name,
                    Client.birthDate == birthdate,
                    Client.deleted == 0
                )
                count = query.count()
                if count > 1:
                    raise Exception(u'Слишком много совпадений по пациенту')
                elif count < 1:
                    raise Exception(u'Не найден пациент')
                client = query.first()
        if client is None:
            raise Exception(u'Не найден пациент')
        self.client = client
        return self
