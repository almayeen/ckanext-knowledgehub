import datetime

import ckan.logic as logic
from ckan import model
from ckan.model.meta import metadata, mapper, Session
from ckan.model.types import make_uuid
from ckan.model.domain_object import DomainObject

from sqlalchemy import types, ForeignKey, Column, Table, desc, asc, or_

__all__ = [
    'RNNCorpus',
    'rnn_corpus_table',
    'setup'
]

rnn_corpus_table = None


class RNNCorpus(DomainObject):

    @classmethod
    def get(cls, id_or_name=None, **kwargs):
        q = kwargs.get('q')
        limit = kwargs.get('limit')
        offset = kwargs.get('offset')
        order_by = kwargs.get('order_by')

        kwargs.pop('q', None)
        kwargs.pop('limit', None)
        kwargs.pop('offset', None)
        kwargs.pop('order_by', None)

        query = Session.query(cls).autoflush(False)
        query = query.filter_by(**kwargs)

        if id_or_name:
            query = query.filter(
                or_(cls.id == id_or_name, cls.content == id_or_name)
            )

        if q:
            query = query.filter(
                or_(cls.content.contains(q),
                    cls.content.ilike(r"%{}%".format(q)))
            )

        if order_by:
            query = query.order_by(order_by)

        if limit:
            query = query.limit(limit)

        if offset:
            query = query.offset(offset)

        return query

    @classmethod
    def update(cls, filter, data):
        obj = Session.query(cls).filter_by(**filter)
        obj.update(data)
        Session.commit()

        return obj.first()

    @classmethod
    def delete(cls, filter):
        obj = Session.query(cls).filter_by(**filter).first()
        if obj:
            Session.delete(obj)
            Session.commit()
        else:
            raise logic.NotFound


rnn_corpus_table = Table(
    'rnn_corpus',
    metadata,
    Column(
        'id',
        types.UnicodeText,
        primary_key=True,
        default=make_uuid),
    Column(
        'corpus',
        types.UnicodeText,
        nullable=False),
    Column(
        'created_at',
        types.DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow)
)


mapper(
    RNNCorpus,
    rnn_corpus_table,
)


def setup():
    metadata.create_all(model.meta.engine)
