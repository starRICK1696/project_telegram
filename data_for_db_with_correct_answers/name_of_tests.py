import sqlalchemy
from .db_session import SqlAlchemyBase


class Nameoftest(SqlAlchemyBase):
    __tablename__ = 'name_of_tests'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=False)