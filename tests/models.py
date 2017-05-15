from sqlalchemy.schema import MetaData
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Date
from sqlalchemy import sql
from sqlalchemy.ext.declarative import declarative_base




class ModelsBase:
    async def reset(self, conn):
        for table in self.metadata.sorted_tables[::-1]:
            try:
                await conn.execute(sql.ddl.DropTable(table))
            except Exception:
                pass
        for table in self.metadata.sorted_tables:
            await conn.execute(sql.ddl.CreateTable(table))


def create_models1():
    class Models1(ModelsBase):
        db_id = 'db1'
        metadata = MetaData()
        Base = declarative_base(metadata=metadata)

        class Test(Base):
            __tablename__ = 'Test'
            id = Column(Integer, primary_key=True)
            title = Column(String(60), nullable=True)
            title2 = Column(String(60), nullable=True)
            date = Column(Date, nullable=True)

        test_table1 = Test.__table__
    return Models1()

def create_models2():
    class Models2(ModelsBase):
        db_id = 'db2'
        metadata = MetaData()
        Base = declarative_base(metadata=metadata)

        class Test2(Base):
            __tablename__ = 'Test2'
            id = Column(Integer, primary_key=True)
            title = Column(String(60), nullable=True)
            title2 = Column(String(60), nullable=True)

        test_table2 = Test2.__table__
    return Models2()


def create_metadata(models):
    return {model.db_id: model.metadata for model in models}

