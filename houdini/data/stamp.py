from houdini.data import db, BaseCrumbsCollection


class Stamp(db.Model):
    __tablename__ = 'stamp'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    group_id = db.Column(db.ForeignKey('stamp_group.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    member = db.Column(db.Boolean, nullable=False, server_default=db.text("false"))
    rank = db.Column(db.SmallInteger, nullable=False, server_default=db.text("1"))
    description = db.Column(db.String(255), nullable=False, server_default=db.text("''::character varying"))


class StampGroup(db.Model):
    __tablename__ = 'stamp_group'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    parent_id = db.Column(db.ForeignKey('stamp_group.id', ondelete='CASCADE', onupdate='CASCADE'))


class CoverStamp(db.Model):
    __tablename__ = 'cover_stamp'

    penguin_id = db.Column(db.ForeignKey('penguin.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True,
                           nullable=False)
    stamp_id = db.Column(db.ForeignKey('stamp.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True,
                         nullable=False)
    x = db.Column(db.SmallInteger, nullable=False, server_default=db.text("0"))
    y = db.Column(db.SmallInteger, nullable=False, server_default=db.text("0"))
    rotation = db.Column(db.SmallInteger, nullable=False, server_default=db.text("0"))
    depth = db.Column(db.SmallInteger, nullable=False, server_default=db.text("0"))


class CoverItem(db.Model):
    __tablename__ = 'cover_item'

    penguin_id = db.Column(db.ForeignKey('penguin.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True,
                           nullable=False)
    item_id = db.Column(db.ForeignKey('item.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True,
                        nullable=False)
    x = db.Column(db.SmallInteger, nullable=False, server_default=db.text("0"))
    y = db.Column(db.SmallInteger, nullable=False, server_default=db.text("0"))
    rotation = db.Column(db.SmallInteger, nullable=False, server_default=db.text("0"))
    depth = db.Column(db.SmallInteger, nullable=False, server_default=db.text("0"))


class PenguinStamp(db.Model):
    __tablename__ = 'penguin_stamp'

    penguin_id = db.Column(db.ForeignKey('penguin.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True,
                           nullable=False)
    stamp_id = db.Column(db.ForeignKey('stamp.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True,
                         nullable=False)
    recent = db.Column(db.Boolean, nullable=False, server_default=db.text("true"))


class StampCrumbsCollection(BaseCrumbsCollection):

    def __init__(self, inventory_id=None):
        super().__init__(model=Stamp,
                         key='id',
                         inventory_model=PenguinStamp,
                         inventory_key='penguin_id',
                         inventory_value='stamp_id',
                         inventory_id=inventory_id)
