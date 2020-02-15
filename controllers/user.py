
def index():
    return dict()

def users_component():
    grid = SQLFORM.smartgrid(db.auth_user, csv=False)
    return dict(grid=grid)

