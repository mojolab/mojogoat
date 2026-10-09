mongod --dbpath /xpal-data/db --logappend --fork --logpath /xpal-data/db/mongod.log
 /usr/lib/postgresql/14/bin/pg_ctl -D /xpal-data/pgdata -l logfile start