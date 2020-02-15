# -*- coding: utf-8 -*-

@auth.requires_membership('admin')
def index():
    grid = SQLFORM.grid(db.problem)
    return dict(grid=grid)

@auth.requires_login()
def add():
    form = SQLFORM(db.problem)

    if form.process().accepted:
        response.flash = T("The problem ha being sent")
    return dict(form=form)

def component():

    if request.post_vars.point:
        problem_id = int(request.post_vars.problem_id)
        point_value = int(request.post_vars.point)
        vote = db((db.vote.auth_user == auth.user.id) & (db.vote.problem == problem_id)).select().first()
        if not vote:
            db.vote.insert(vote=point_value, auth_user=auth.user.id, problem=problem_id)
            db.commit()


    def plus_button(row):
        if auth.user and not db((db.vote.auth_user == auth.user.id) & (db.vote.problem == row.id)).select().first():
            return FORM(INPUT(_name='problem_id', _value=row.id, _type='hidden'),
                        INPUT(_name='point', _value='1', _type='hidden'),
                        BUTTON('+'))
        return ''

    def minus_button(row):
        if auth.user and not db((db.vote.auth_user == auth.user.id) & (db.vote.problem == row.id)).select().first():
            return FORM(INPUT(_name='problem_id', _value=row.id, _type='hidden'),
                        INPUT(_name='point', _value='-1', _type='hidden'),
                        BUTTON('-'))
        return ''

    grid = SQLFORM.grid(db.problem,
                        editable=False,
                        deletable=False,
                        create=False,
                        details=False,
                        csv=False,
                        links=[
                            {
                                'header': '',
                                'body': plus_button
                            },
                            {
                                'header': '',
                                'body': minus_button
                            },
                        ],
                        )
    return dict(grid=grid)