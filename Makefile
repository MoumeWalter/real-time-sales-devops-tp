up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

test:
	python3 -m pytest tests/unit -v

clean:
	docker compose down -v
