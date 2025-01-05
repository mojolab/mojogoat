'''
API to parse recieve messages and parse GOAT commands
'''
# TODO: #1 FEATURE - Add a command to process facts as distict from relationships
# TODO: #2 FEATURE - Add a command to process meeting notes
# TODO: #3 FEATURE - Add a command to delete new lines by message reply
# TODO: #4 OPTIMIZE - Standardize command function nomencalture and taxonomy
# TODO: #6 ARCHITECTURE - Read labels from a schema file
# TODO: #7 ARCHITECTURE - Read object schemas from a schema file
# TODO: #8 ARCHITECTURE - Use appropriate stores for appropriate data - line records for relationships and doc records on entities

from mojogoat import *
from mojogoat.mojogoat.goatbases.mongogoat.models import Node

from .goatbases.textgoat import *
from .utils import *
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mongoengine import MongoEngine
import io, os, re, sys
from flask_cors import CORS, cross_origin
'''
app = Flask(__name__)
CORS(app)
global herd_config
# herd_config=read_herd_config(sys.argv[-1])
herd_config=read_herd_config("/xpal-data/conf/sampleconfig.json")
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
migrate = Migrate()
migrate.init_app(app, sqldb)
db = MongoEngine(app)



from mojogoat import routes
'''

if __name__ == '__main__':
    
    app.run(debug=True, host='0.0.0.0',port='5000')





    
