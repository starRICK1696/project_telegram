import sqlalchemy
from .db_session import SqlAlchemyBase


class Questionandanswer(SqlAlchemyBase):
    __tablename__ = 'questions_and_answers'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    question = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    answer = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    name_of_test = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    explanation = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    number_of_question = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)