# -*- coding: utf-8 -*-

response.menu = [
    (T('Home'), False, URL('default', 'index'), []),
]

if auth.user:
    response.menu += [
        (T('Add problem'), False, URL('problem', 'add'), []),
    ]



if auth.has_membership('admin'):
    response.menu += [
        (T('Problems'), False, URL('problem', 'index'), []),
        (T('Users'), False, URL('user', 'index'), []),
    ]