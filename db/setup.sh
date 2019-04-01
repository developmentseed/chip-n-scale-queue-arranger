DATABASE_URL=$1
DATABASE_URL=$DATABASE_URL knex migrate:latest --env remote --knexfile db/knexfile.js
