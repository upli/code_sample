# -*- coding: utf-8 -*-
import string

import xlrd
import xlwt

from cStringIO import StringIO

from functools32 import lru_cache
from lxml import etree


class XlsReader(object):
    def __init__(self, *args, **kwargs):
        self.book = xlrd.open_workbook(*args, **kwargs)

    def get_cells(self, row_num, col_letters, sheet_index=0):
        """Извлекает содержимое cells на строке row_num.

        :param row_num:     Номер строки, нумерация с единицы
        :param col_letters: Итерируемый объект, содержащий последовательность извлечения колонок
        :param sheet_index: Номер листа
        :return:            str | Содержание из cells на строке row_num
        """
        sheet = self.book.sheet_by_index(sheet_index)
        return u''.join([
            sheet.cell_value(row_num - 1, self._col2num(col_let) - 1)
            for col_let in col_letters
        ])

    def get_cells_by_label(self, label, col_let, col_letters, sheet_index=0):
        """Ищет строку, в которой находится искомый текст (label).
        Далее извлекает содержимое из этой строки.

        :param label:       Текст, по которому ищем номер строки
        :param col_let:     Буква колонки, в которой ищем label
        :param col_letters: Итерируемый объект, содержащий последовательность извлечения колонок
        :param sheet_index: Номер листа
        :return:            str | Содержание из cells на строке с label
        """
        result = ''
        row_num = self._find_row_by_label(label, col_let, sheet_index)
        if row_num:
            result = self.get_cells(row_num, col_letters, sheet_index)
        return result

    @staticmethod
    @lru_cache()
    def _col2num(col):
        """Преобразует буквенное название колонки в числовое"""
        num = 0
        for c in col:
            if c in string.ascii_letters:
                num = num * 26 + (ord(c.upper()) - ord('A')) + 1
        return num

    def _find_row_by_label(self, label, col_let, sheet_index=0):
        """Ищет строку, в которой находится искомый текст (label).
        Возвращает номер строки. Нумерация с нуля.

        :param label:       Искомая строка
        :param col_let:     Буква колонки, в которой ищем
        :param sheet_index: Номер листа
        :return:            int | номер строки
        """
        sheet = self.book.sheet_by_index(sheet_index)
        for row_num in xrange(sheet.nrows):
            cell_val = sheet.cell_value(row_num, self._col2num(col_let) - 1)
            if cell_val and cell_val.strip().lower() == label.lower():
                return row_num + 1


def html2xls(html_str):
    """Преобразует таблицы из html файла в xls. Возвращает объект класса `StringIO`"""
    parser = etree.HTMLParser()
    root = etree.parse(StringIO(html_str), parser)
    book = xlwt.Workbook()
    sheet = book.add_sheet("Sheet")

    for n, tr in enumerate(root.find('.//table').findall('tr')):
        row = sheet.row(n)
        for l, td in enumerate(tr.findall('td')):
            row.write(l, td.text)

    stream_book = StringIO()
    book.save(stream_book)
    stream_book.seek(0)
    return stream_book
