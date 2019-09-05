build:
	
deploy:
	zip -g function.zip lambda_function.py settings.json
	aws lambda update-function-code --function-name getmyip --zip-file fileb://function.zip