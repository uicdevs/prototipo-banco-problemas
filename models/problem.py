
def _on_problem_define(table):
    table.points.writable = False


db.define_table('problem',
                Field('name', 'string',
                      requires=IS_NOT_EMPTY(), label=T('Name')),
                Field('description', 'text',
                      requires=IS_NOT_EMPTY(), label=T('Description')),
                Field('points', 'integer', default=0, label=T('Points')),
                auth.signature,
                on_define=_on_problem_define,
                )