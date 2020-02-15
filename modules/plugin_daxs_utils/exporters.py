import base64
import csv
from io import StringIO

from gluon._compat import PY2, long
from gluon.packages.dal.pydal.objects import Field
from gluon.packages.dal.pydal.helpers.classes import Reference
from gluon.packages.dal.pydal.helpers.methods import bar_encode
from gluon.packages.dal.pydal.objects import Row
from gluon.sqlhtml import ExportClass


class ExporterCSVColnames(ExportClass):
    # CSV, represent == True
    label = 'CSV'
    file_ext = "csv"
    content_type = "text/csv"

    def __init__(self, rows, null='<NULL>', colnames=None, uselabels=False, exclude=None):
        ExportClass.__init__(self, rows)
        self.colnames=colnames
        self.uselabels=uselabels
        self.exclude=exclude
        self.null=null

    def export(self):  # export CSV with rows.represent
        if self.rows:
            s = StringIO()
            if self.colnames:
                export_to_csv_file(self.rows, s, null=self.null, represent=True, uselabels=self.uselabels, exclude=self.exclude,  colnames=self.colnames)
            else:
                export_to_csv_file(self.rows, s, null=self.null, represent=True, uselabels=self.uselabels, exclude=self.exclude)
            return s.getvalue()
        else:
            return None

class ExporterFakeExcelColnames(ExporterCSVColnames):
    label = 'Excel'
    file_ext = "xls"
    content_type = "application/vnd.ms-excel"

    def __init__(self, rows, null='<NULL>', colnames=None, uselabels=False, exclude=None):
        super().__init__(rows, null=null, colnames=colnames, uselabels=uselabels, exclude=exclude)

def export_to_csv_file(self, ofile, null='<NULL>', *args, **kwargs):
    """
    Exports data to csv, the first line contains the column names

    Args:
        ofile: where the csv must be exported to
        null: how null values must be represented (default '<NULL>')
        delimiter: delimiter to separate values (default ',')
        quotechar: character to use to quote string values (default '"')
        quoting: quote system, use csv.QUOTE_*** (default csv.QUOTE_MINIMAL)
        represent: use the fields .represent value (default False)
        colnames: list of column names to use (default self.colnames)

    This will only work when exporting rows objects!!!!
    DO NOT use this with db.export_to_csv()
    """
    delimiter = kwargs.get('delimiter', ',')
    quotechar = kwargs.get('quotechar', '"')
    quoting = kwargs.get('quoting', csv.QUOTE_MINIMAL)
    represent = kwargs.get('represent', False)
    writer = csv.writer(ofile, delimiter=delimiter,
                        quotechar=quotechar, quoting=quoting)
    uselabels = kwargs.get('uselabels', False)
    exclude = kwargs.get('exclude', [])

    def unquote_colnames(colnames):

        unq_colnames = []

        def get_name(col):
            name = None
            m = self.db._adapter.REGEX_TABLE_DOT_FIELD.match(col)
            if not m:
                name = col
            else:
                name = '.'.join(m.groups())
            return name

        if uselabels:
            for col in colnames:
                m = self.db[col.split('.')[0]][col.split('.')[1]].label
                unq_colnames.append(m)
        else:
            for col in colnames:
                m = get_name(col)
                unq_colnames.append(m)
        return unq_colnames

    colnames = kwargs.get('colnames', self.colnames)

    if exclude:
        for col in exclude:
            colnames.remove(col)

    write_colnames = kwargs.get('write_colnames', True)
    # a proper csv starting with the column names
    if write_colnames:
        writer.writerow(unquote_colnames(colnames))

    def none_exception(value):
        """
        Returns a cleaned up value that can be used for csv export:

        - unicode text is encoded as such
        - None values are replaced with the given representation (default <NULL>)
        """
        if value is None:
            return null
        elif PY2 and isinstance(value, unicode):
            return value.encode('utf8')
        elif isinstance(value, Reference):
            return long(value)
        elif hasattr(value, 'isoformat'):
            return value.isoformat()[:19].replace('T', ' ')
        elif isinstance(value, (list, tuple)):  # for type='list:..'
            return bar_encode(value)
        return value

    repr_cache = {}

    fieldlist = []
    for f in self.fields:
        field_str = '{table}.{name}'.format(table=f.table, name=f.name)
        if field_str in colnames:
            fieldlist.append(f if f.__class__.__name__ == 'Field' else None)

    fieldmap = dict(zip(self.colnames, fieldlist))
    for record in self:
        row = []
        for col in colnames:
            field = fieldmap[col]
            if field is None:
                row.append(record._extra[col])
            else:
                t, f = field._tablename, field.name
                if isinstance(record.get(t, None), (Row, dict)):
                    value = record[t][f]
                else:
                    value = record[f]
                if field.type == 'blob' and value is not None:
                    value = base64.b64encode(value)
                elif represent and field.represent:
                    if field.type.startswith('reference'):
                        if field not in repr_cache:
                            repr_cache[field] = {}
                        if value not in repr_cache[field]:
                            repr_cache[field][value] = field.represent(
                                value, record
                            )
                        value = repr_cache[field][value]
                    else:
                        value = field.represent(value, record)
                row.append(none_exception(value))
        writer.writerow(row)
