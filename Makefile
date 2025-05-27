upgrade:
	alembic upgrade head

restart:
	sudo systemctl daemon-reload
	sudo systemctl restart vv_bot.service

status:
	sudo systemctl status vv_bot.service
logs:
	sudo journalctl -u vv_bot.service -f

logs-all:
	sudo journalctl -u vv_bot.service --no-pager