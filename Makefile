.PHONY: build deploy clean remove-dev setup-dev

setup-dev:
	pipenv install
	pipenv shell

remove-dev:
	 pipenv uninstall --all

build:
	python ./buildutil.py
	
deploy:
	cdk deploy