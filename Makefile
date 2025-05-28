.PHONY: db-migrate db-create db-downgrade db-verify db-backup

# Database migration commands
db-migrate:
	python manage_db.py migrate

db-create:
	python manage_db.py create "$(message)"

db-downgrade:
	python manage_db.py migrate --downgrade $(revision)

db-verify:
	python manage_db.py migrate --verify

db-backup:
	python backup_db.py 