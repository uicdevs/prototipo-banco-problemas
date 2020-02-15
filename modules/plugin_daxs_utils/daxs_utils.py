from gluon import current
from gluon import HTTP
from  gluon.html import *
T = current.T

def request_type(request_type):
    """
    Decorator that will only accept selected request types, will rise a bad request error code (400)
    if is not a selected request
    :param request_type: A string or a list of strings containing accepted requests
    """
    def real_decorator(f):
        def wrapper(*args, **kwargs):
            if (type(request_type) is list) and (current.request.env.request_method not in request_type):
                raise HTTP(400)
            elif (type(request_type) is not list) and (current.request.env.request_method != request_type):
                raise HTTP(400)
            else:
                return f(*args, **kwargs)
        return wrapper
    return real_decorator

def post_request(f):
    """
    Decorator that will only accept POST requests, will rise an bad request error code (400)
    if is not a POST request
    """
    def wrapper():
        if current.request.env.request_method != 'POST':
            raise HTTP(400)
        else:
            return f()
    return wrapper

def get_request(f):
    """
    Decorator that will only accept GET requests, will rise an bad request error code (400)
    if is not a GET request
    """
    def wrapper():
        if current.request.env.request_method != 'GET':
            raise HTTP(400)
        else:
            return f()
    return wrapper

def get_json_request(f):
    """
    Decorator that will only accept GET requests, will rise an bad request error code (400)
    if is not a GET request
    """
    def wrapper():
        if current.request.env.request_method != 'GET':
            raise HTTP(400)
        else:
            current.response.generic_patterns.append('json')
            return f()
    return wrapper

def put_request(f):
    """
    Decorator that will only accept PUT requests, will rise an bad request error code (400)
    if is not a PUT request
    """
    def wrapper():
        if current.request.env.request_method != 'PUT':
            raise HTTP(400)
        else:
            return f()
    return wrapper

def delete_request(f):
    """
    Decorator that will only accept DELETE requests, will rise an bad request error code (400)
    if is not a DELETE request
    """
    def wrapper():
        if current.request.env.request_method != 'DELETE':
            raise HTTP(400)
        else:
            return f()
    return wrapper


def only_development(config):
    """
    Decorator that will only accept selected request types, will rise a bad request error code (400)
    if is not a selected request
    :param request_type: A string or a list of strings containing accepted requests
    """
    def real_decorator(f):
        def wrapper(*args, **kwargs):
            if current.request.is_local and not config.get('app.production'):
                return f(*args, **kwargs)
            else:
                raise HTTP(403)
        return wrapper
    return real_decorator


def http_error(code):
    """
    Raises an Http code
    :param code: HTTP code
    """
    raise HTTP(code)


def row_table(row, table, name_header=None, value_header=None, header=True, footer=False, fields=None, row_represent=None, **args):
    """
    Displays a row object as a name-value pair table
    :param row: Row to display
    :param table: Row table
    :param name_header: Table header string for name column (default T('Name'))
    :param value_header: Table header string for value column (default T('Value'))
    :param header: Display table header (default True), can be specified a THEAD object
    :param footer: Display table footer (default False), can be specified a THEAD object
    :param fields: List of fields to show in table
    :param row_represent:
    :param args: arguments to pass to TABLE object
    :return: TABLE object
    """
    if not name_header:
        name_header = T('Name')
    if not value_header:
        value_header = T('Value')
    table_list = []

    iter = fields if fields else table

    for field in iter:
        if field.readable:
            pair = []
            pair.append(table[field.name].label)

            if table[field.name].represent:
                pair.append(table[field.name].represent(row[field.name], row))
            else:
                pair.append(str(row[field.name]))

            table_list.append(pair)

    table_parts = []

    table_head = None
    if header is True:
        table_head = THEAD(TR(TH(name_header), TH(value_header)))
    elif header:
        table_head = header

    pairs = []
    for tr_pair in table_list:
        if row_represent:
            row_represented = row_represent(tr_pair)
            if row_represented:
                pairs.append(row_represented)
        else:
            pairs.append(TR(*tr_pair))
    table_body = TBODY(*pairs)

    table_footer = None
    if footer is True:
        table_footer = TFOOT(TR(TH(name_header), TH(value_header)))
    elif footer:
        table_footer = footer

    if table_head:
        table_parts.append(table_head)
    if table_footer:
        table_parts.append(table_footer)
    if table_body:
        table_parts.append(table_body)

    return TABLE(*table_parts, **args)

