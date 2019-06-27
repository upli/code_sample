@module.route('/api/patient_client_diet_list_save.json', methods=['POST'])
@db_non_flushable
@api_method
def api_diet_list_save():
    data = request.get_json() or {}
    client_id = data.get('client_id')
    diets_list = data.get('diets_list', [])
    result = []

    for diet_data in diets_list:
        client_diet = ClientDiet.get_or_create(diet_data.get('id'))
        try:
            client_diet.update_data(client_id, diet_data)
        except ClientDietValidationException, e:
            raise ApiException(400, e.message)

        result.append(client_diet)
        db.session.add(client_diet)

    db.session.commit()
    return result


@module.route('/api/patient_client_diet_list_delete.json', methods=['POST'])
@db_non_flushable
@api_method
def api_diet_list_delete():
    data = request.get_json()
    diets_id_list = data.get('diets_id_list', [])
    ClientDiet.delete_by_ids(diets_id_list)
    db.session.commit()
