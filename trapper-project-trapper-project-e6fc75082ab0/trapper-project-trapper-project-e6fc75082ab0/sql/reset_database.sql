DROP DATABASE trapper_db;
CREATE DATABASE trapper_db;
GRANT ALL PRIVILEGES ON DATABASE trapper_db TO trapper;
\c trapper_db
CREATE EXTENSION hstore;
CREATE EXTENSION postgis;

