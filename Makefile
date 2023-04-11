.PHONY: up
up:
	@docker-compose up --build -d

.PHONY: down
down:
	@docker-compose down

.PHONY: migrate
migrate:
	@docker exec foodService python manage.py migrate --noinput

.PHONY: createuser
createuser:
	@docker exec foodService python manage.py createsuperuser --noinput