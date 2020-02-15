from gluon import current

def add_group(auth, name):
    db = auth.db
    admin_role = db(db.auth_group.role == name).select().first()
    if not admin_role:
        admin_group_id = auth.add_group(name)
    else:
        admin_group_id = admin_role.id
    return admin_group_id

def add_permission(auth, group_id, name, table):
    db = auth.db
    perm = db((db.auth_permission.group_id == group_id) & (db.auth_permission.name == name) & (db.auth_permission.table_name == table._tablename)).select().first()
    if not perm:
        auth.add_permission(group_id, name, table)
    else:
        pass
