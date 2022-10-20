-- psql -U postgres <user> -f <sql_file>

-- Psql basic implementation is stupid, it uses operating system’s file system for its storage, so it would be better to localize the DB
CREATE TABLESPACE deso_space OWNER <user> LOCATION '<path-of-database'

-- Once created a new tablespace, we are allowed to create databases in it
CREATE DATABASE deso_blockchain TABLESPACE deso_space;




