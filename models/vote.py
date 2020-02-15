
def _on_vote_define(table):
    table._after_insert.append(lambda f, i: db(db.problem.id==f.problem).update(points=db.problem.points+f.vote))

db.define_table('vote',
                Field('vote', 'integer',
                      requires=IS_IN_SET([-1,1]), label=T('Name')),
                Field('auth_user', 'reference:auth_user'),
                Field('problem', 'reference:problem'),
                auth.signature,
                on_define=_on_vote_define,
                )
