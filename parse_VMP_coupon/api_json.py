@module.route('/api/patient_coupon_parse.json', methods=['POST'])
@api_method
def api_patient_coupon_parse():
    data = request.json
    finance_id = data.get('finance_id')
    coupon_file = data['coupon']
    file_content = coupon_file.get('binary_b64')
    head, content = file_content.split(',')
    coupon = VMPCoupon.from_zip(content, finance_id)

    if not coupon.quotaType:
        raise ApiException(422, u'Не найдено подходящей квоты по коду "{0}", дате "{1}" '
                                u'и источнику финансирования'.format(
            coupon.parsed.get('quota_type_code'), format_date(coupon.parsed.get('quota_date'))
        ))
    coupon.fileLink = file_content

    return coupon
