class OrmError(Exception):
    pass

class ItemNotFoundError(OrmError):
    pass

class ItemAlreadyExistsError(OrmError):
    pass
