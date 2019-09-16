#!/usr/bin/env python3

from aws_cdk.core import App, Construct, Duration
from aws_cdk import (
    core,
    aws_lambda as awslambda,
    aws_apigateway as apigw,
    aws_dynamodb as dynamodb,
    aws_ec2 as ec2
)

from aws.aws_stack import AwsStack

class PastebinScraperStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # only add 1 NATGW for cost savings
        # remove the parameter or set explicitly for HA across 2 AZs
        vpc = ec2.Vpc(self, "VPC", nat_gateways=1)

        part_key = dynamodb.Attribute(name="key", type=dynamodb.AttributeType.STRING)
        table = dynamodb.Table(self, "pastebin-items",
                                   partition_key=part_key,
                                   read_capacity=10,
                                   write_capacity=5)

        scraper_lambda = awslambda.Function(
            self, 'PastebinScraper',
            runtime=awslambda.Runtime.PYTHON_3_7,
            code=awslambda.Code.asset('./lambda'),
            handler=''

        # pass the table name to the handler through an environment variable and grant
        # the handler read/write permissions on the table.
        handler.add_environment('TABLE_NAME', table.table_name)
        table.grant_read_write_data(handler)

        )

app = core.App()
PastebinScraperStack(app, "pastebin-app")

app.synth()
