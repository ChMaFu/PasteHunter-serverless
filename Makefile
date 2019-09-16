S3_BUCKET=pastehunter
ENV_CF_YAML=PasteHunterAWSEnvironment.yaml
STACK_NAME=PasteHunterEnv

prep-setupenv:
	./script/create-aws-env.sh

execute-setup:
	./script/execute-aws-env-change.sh

prep-updateenv:
	aws s3 cp ./$(ENV_CF_YAML) s3://$(S3_BUCKET)/cf/
	aws cloudformation create-change-set --stack-name $(STACK_NAME) --change-set-name updateenv --change-set-type UPDATE --use-previous-template

check-status:
	aws cloudformation describe-change-set --change-set-name setupenv --stack-name $(STACK_NAME)

execute-update:
	aws cloudformation execute-change-set --change-set-name setupenv --stack-name $(STACK_NAME)

delete-aws-env:
	./script/delete-aws-env.sh

listenvs:
	aws cloudformation list-stacks --stack-status-filter CREATE_IN_PROGRESS CREATE_FAILED CREATE_COMPLETE ROLLBACK_IN_PROGRESS ROLLBACK_COMPLETE | jq '.StackSummaries | .[] | {stack: .StackName, status: .StackStatus}'

setup-dev:
	conda create -n pastehunter python=3.7
	pip install -r requirements.txt
	echo ">>> Run the following to activate the environment: conda activate pastehunter <<<"

remove-dev:
	bash -l -c "conda deactivate"
	conda-env remove -n pastehunter

build:
	sam package --template-file template.yaml --s3-bucket pastehunter --output-file packaged.yaml
	
deploy:
	sam deploy --template-file ./packaged.yaml --stack-name pastehunter-lambda --capabilities CAPABILITY_IAM
	#zip -g function.zip lambda_function.py settings.json
	#aws lambda update-function-code --function-name getmyip --zip-file fileb://function.zip