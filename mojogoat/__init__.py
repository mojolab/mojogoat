#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Sun Sep 30 03:10:53 2018

@author: arjun
"""
from .goat import *
from .utils import *
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mongoengine import MongoEngine
import io, os, re, sys


app = Flask(__name__)

global herd_config
herd_config=read_herd_config(sys.argv[1])
goatpen=herd_config['goatpen']
goatlog=os.path.join(goatpen,"goatlog")
global herd
herd=get_goats(herd_config)
global curgoat
curgoat=herd[0]


app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:postgres@localhost:5432/xetrapal"
app.config['MONGODB_SETTINGS'] = {
    'host':'mongodb://localhost/'+curgoat.goatname
}

sqldb = SQLAlchemy()
sqldb.init_app(app)
migrate = Migrate(app, sqldb)
db = MongoEngine(app)



from mojogoat import routes