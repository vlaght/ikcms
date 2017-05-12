from sqlalchemy.exc import IntegrityError

class OrmError(Exception):
    pass

class ItemNotFoundError(OrmError):
    pass

class ItemAlreadyExistsError(OrmError):
    pass

