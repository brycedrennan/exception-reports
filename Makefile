python_version = 3.6.6
venv_prefix = exc-reports
venv_name = $(venv_prefix)-$(python_version)

init:
	@if ! [ -x "$$(command -v pyenv)" ]; then\
	  echo 'Error: pyenv is not installed.';\
	  exit 1;\
	fi
	pyenv install $python_version -s
	if ! [ -d "$$(pyenv root)/versions/$(venv_name)" ]; then\
		pyenv virtualenv 3.6.6 $(venv_name);\
	fi;
	pyenv local $(venv_name)
	pip install --upgrade pip pre-commit
	pip install -r requirements.txt --upgrade
	@pre-commit install
	@echo "\nNew virtualenv created. Copy this path to tell PyCharm where it is:\n"
	@pyenv which python
	@echo "\n"

autoformat:
	@black .

test:
	@pytest -n auto

lint:
	@pylava

deploy:
	pip install twine wheel
	git tag $$(python setup.py -V)
	git push --tags
	python setup.py bdist_wheel
	python setup.py sdist
	@echo 'pypi.org Username: '
	@read username && twine upload dist/* -u $$username;
