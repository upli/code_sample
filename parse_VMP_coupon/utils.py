import base64
import zipfile

import qrcode

from cStringIO import StringIO


def unzip2dict(zip_str_b64):
    """Распакует файлы в строку и положит в словарь"""
    result = {}
    zip_str = base64.b64decode(zip_str_b64)
    zip_stream = StringIO(zip_str)
    zip_file = zipfile.ZipFile(zip_stream)
    for file_name in zip_file.namelist():
        result[file_name] = zip_file.open(file_name).read()

    return result


def get_qr_code_base64(input_sting, **kwargs):
    """Преобразует входную строку в QR изображение формата png в кодировке base64.

    :param input_sting: Входная строка с данными
    :return: Изображение png в кодировке base64
    :rtype: str
    """
    file_buffer = StringIO()
    img = qrcode.make(input_sting, **kwargs)
    img.save(file_buffer, 'png')
    return base64.b64encode(file_buffer.getvalue())
