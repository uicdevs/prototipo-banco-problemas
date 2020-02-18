# -*- coding: utf-8 -*-
from plugin_daxs_utils import only_development
from plugin_daxs_utils import auth as daxs_auth


def index():
    return dict(message=T('Welcome to web2py!'))


@only_development(configuration)
def populate_db():

    admin_group_id = daxs_auth.add_group(auth, 'admin')

    # add admin user
    admin_user_id = db.auth_user.insert(
        first_name='Administrator',
        last_name='Master',
        password=db.auth_user.password.validate('123admin321')[0],
        email='admin@admin.com',
    )

    auth.add_membership(admin_group_id, admin_user_id)

    return 'ok'

# @post_request
def login_and_take_token():
    return AppJWT.jwt_token_manager()

# @auth.requires_login()
@AppJWT.allows_jwt(required=False)
@request.restful()
def api():
    response.view = 'generic.'+request.extension

    def GET(*args,**vars):

        # allows only unauthenticated access to problem api endpoints
        if args[0] != 'problem' and not auth.user:
            raise HTTP(403)

        patterns = [
            '/problem[problem]',
            ':auto[problem]',

            '/vote[vote]',
            ':auto[vote]',

            ':auto[auth_user]'
        ]
        parser = db.parse_as_rest(patterns,args,vars)
        if parser.status == 200:
            return dict(content=parser.response)
        else:
            raise HTTP(parser.status,parser.error)

    def POST(table_name,**vars):
        if (not auth.user and table_name != 'problem') and not auth.requires_membership('admin'):
            raise HTTP(403)
        return db[table_name].validate_and_insert(**vars)
    def PUT(table_name,record_id,**vars):
        if not auth.requires_membership('admin'):
            raise HTTP(403)
        return db(db[table_name]._id==record_id).update(**vars)
    def DELETE(table_name,record_id):
        if not auth.requires_membership('admin'):
            raise HTTP(403)
        return db(db[table_name]._id==record_id).delete()

    return dict(GET=GET, POST=POST, PUT=PUT, DELETE=DELETE)

# ---- Action for login/register/etc (required for auth) -----
def user():
    """
    exposes:
    http://..../[app]/default/user/login
    http://..../[app]/default/user/logout
    http://..../[app]/default/user/register
    http://..../[app]/default/user/profile
    http://..../[app]/default/user/retrieve_password
    http://..../[app]/default/user/change_password
    http://..../[app]/default/user/bulk_register
    use @auth.requires_login()
        @auth.requires_membership('group name')
        @auth.requires_permission('read','table name',record_id)
    to decorate functions that need access control
    also notice there is http://..../[app]/appadmin/manage/auth to allow administrator to manage users
    """
    return dict(form=auth())

# ---- action to server uploaded static content (required) ---
@cache.action()
def download():
    """
    allows downloading of uploaded files
    http://..../[app]/default/download/[filename]
    """
    return response.download(request, db)
