lint:
	pylava

test:
	pytest

autoformat:
	black --py36 -l 130 --exclude \.direnv .
