#!/usr/bin/python
# -*- coding: utf-8 -*-
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, MetaData, Sequence, ForeignKey
from sqlalchemy import BigInteger, DateTime
from sqlalchemy.orm import sessionmaker, backref, relationship
from enum import Enum
import hashlib
import logging
import logging.handlers
import os

logger = logging.getLogger(__name__)

Base = declarative_base()

UserState = Enum('UNVERIFIED', "ACTIVE", "DISABLED")

ses = None
eng = None


#============================
class User(Base):
    __tablename__ = 'USERS'
    id = Column('id', Integer, Sequence('user_id_seq'), primary_key=True)
    name = Column(String(50), unique=True)
    email = Column(String(50))
    state = Column(Integer)
    password = Column(String(50))
    zones = relationship("Zone", backref="user")
    created = Column(DateTime(timezone=True))

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
           'id': self.user_id,
           'name': self.name,
           'email': self.email,
           'state': self.state,
           # 'modified_at': dump_datetime(self.modified_at),
           # This is an example how to deal with Many2Many relations
           'zones': self.serialize_zones
           }

    @property
    def serialize_zones(self):
        """
        Return object's relations in easily serializeable format.
        NB! Calls many2many's serialize property.
        """
        return [item.serialize for item in self.zones]


#================================================
class Zone(Base):
    __tablename__ = 'ZONES'
    id = Column('id', Integer, Sequence('zone_id_seq'), primary_key=True)
    name = Column(String(128))
    description = Column(String(4096))
    user_id = Column(Integer, ForeignKey('USERS.id'))
    # user = relationship("User", backref=backref('zones', order_by=id))
    cameras = relationship("Camera", backref='zone')
    created = Column(DateTime(timezone=True))


    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
           'id': self.id,
           'name': self.name,
           'description': self.description
        }


#================================================
class Camera(Base):
    __tablename__ = 'CAMERAS'
    id = Column('id', Integer, Sequence('camera_id_seq'), primary_key=True)
    name = Column(String(128))
    description = Column(String(4096))
    os_id = Column(Integer, default=0)
    zone_id = Column(Integer, ForeignKey('ZONES.id'))
    images = relationship("Image", backref='camera')
    created = Column(DateTime(timezone=True))


#================================================
class Image(Base):
    __tablename__ = 'IMAGES'
    id = Column('id', BigInteger, Sequence('image_id_seq'), primary_key=True)
    camera_id = Column(Integer, ForeignKey('CAMERAS.id'))
    timestamp = Column(DateTime(timezone=True))
    filename = Column(String(50))
    x_res = Column(Integer)
    y_res = Column(Integer)
    fmt = Column(String(20))


#================================================
class Settings(Base):
    __tablename__ = 'SETTINGS'
    id = Column('id', Integer, Sequence('settings_id_seq'), primary_key=True)
    name = Column(String(100))
    description = Column(String(250))
    value = Column(String(4096))
    last_updated = Column(DateTime(timezone=True))


#================================================
def passwordFromString(stringPassword):
    m = hashlib.md5()
    m.update(stringPassword)
    return m.hexdigest()


#================================================
def dump_datetime(value):
    """Deserialize datetime object into string form for JSON processing."""
    if value is None:
        return None
    return [value.strftime("%Y-%m-%d"), value.strftime("%H:%M:%S")]


#================================================
def get_session():
    global ses
    global eng
    if not ses:
        logger.debug('We are at %s' % os.getcwd())
        eng = create_engine('sqlite:///../homesec.db', echo=True)
        Base.metadata.bind = eng
        Session = sessionmaker(bind=eng)
    return Session()


#===============================================
def schema_create():
    ses = get_session()
    meta = MetaData()
    meta.reflect(bind=eng)
    logger.debug('Creating tables')
    Base.metadata.create_all()
    if not ses.query(User).count():
        logger.debug("Creating default user")
        ses.add(User(name='pi', password=passwordFromString('123456')))
        ses.commit()

    if not ses.query(Settings).count():
        Settings(name='server_url', value='http://localhost:5050')
        ses.commit()

#===========================================================
def setDalLogger(lg):
    global logger
    logger = lg
