"""CDK stack for Agentic Tax Calculator supporting resources.

Provisions DynamoDB tables (shared-state + memory) and IAM roles for
AgentCore Runtime.  The AgentCore Runtime itself is provisioned by
``agentcore deploy`` - this stack only creates the resources that
AgentCore depends on.

Usage:
    cdk deploy --app "python infra/cdk_app.py"

Requirements: 1.1, 1.2
"""

import os

from aws_cdk import (
    App,
    CfnOutput,
    RemovalPolicy,
    Stack,
    Tags,
)
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from constructs import Construct


class AgenticTaxCalculatorStack(Stack):
    """Supporting infrastructure for the Agentic Tax Calculator."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        env = os.environ.get("TAX_CALC_ENV", "dev")

        # -- Shared State table (LangGraph checkpointer) ---------------------
        self.shared_state_table = dynamodb.Table(
            self,
            "SharedStateTable",
            table_name=f"tax-calc-shared-state-{env}",
            partition_key=dynamodb.Attribute(
                name="PK", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="SK", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=(
                RemovalPolicy.DESTROY if env == "dev" else RemovalPolicy.RETAIN
            ),
            time_to_live_attribute="ttl",
            point_in_time_recovery=env != "dev",
        )

        # -- Long-Term Memory table ------------------------------------------
        self.memory_table = dynamodb.Table(
            self,
            "MemoryTable",
            table_name=f"tax-calc-memory-{env}",
            partition_key=dynamodb.Attribute(
                name="PK", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="SK", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=(
                RemovalPolicy.DESTROY if env == "dev" else RemovalPolicy.RETAIN
            ),
            time_to_live_attribute="ttl",
            point_in_time_recovery=env != "dev",
        )

        # -- IAM Role for AgentCore Runtime ----------------------------------
        self.runtime_role = iam.Role(
            self,
            "AgentCoreRuntimeRole",
            role_name=f"tax-calc-agentcore-runtime-{env}",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("bedrock.amazonaws.com"),
                iam.ServicePrincipal("lambda.amazonaws.com"),
            ),
            description="IAM role for AgentCore Runtime executing the Agentic Tax Calculator",
        )

        # DynamoDB read/write on both tables
        self.shared_state_table.grant_read_write_data(self.runtime_role)
        self.memory_table.grant_read_write_data(self.runtime_role)

        # Bedrock model invocation (for LLM calls if needed)
        self.runtime_role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockModelInvocation",
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=["*"],
            )
        )

        # AgentCore Memory API access
        self.runtime_role.add_to_policy(
            iam.PolicyStatement(
                sid="AgentCoreMemoryAccess",
                actions=[
                    "bedrock:CreateMemory",
                    "bedrock:GetMemory",
                    "bedrock:DeleteMemory",
                    "bedrock:CreateEvent",
                    "bedrock:ListEvents",
                    "bedrock:RetrieveMemoryRecords",
                ],
                resources=["*"],
            )
        )

        # CloudWatch Logs for observability
        self.runtime_role.add_to_policy(
            iam.PolicyStatement(
                sid="CloudWatchLogs",
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=["arn:aws:logs:*:*:log-group:/tax-calc/calculator*"],
            )
        )

        # X-Ray tracing
        self.runtime_role.add_to_policy(
            iam.PolicyStatement(
                sid="XRayTracing",
                actions=[
                    "xray:PutTraceSegments",
                    "xray:PutTelemetryRecords",
                ],
                resources=["*"],
            )
        )

        # -- Tags ------------------------------------------------------------
        Tags.of(self).add("Project", "agentic-tax-calculator")
        Tags.of(self).add("Environment", env)

        # -- Outputs ---------------------------------------------------------
        CfnOutput(
            self, "SharedStateTableName",
            value=self.shared_state_table.table_name,
            description="DynamoDB table for LangGraph shared state",
        )
        CfnOutput(
            self, "MemoryTableName",
            value=self.memory_table.table_name,
            description="DynamoDB table for long-term memory",
        )
        CfnOutput(
            self, "RuntimeRoleArn",
            value=self.runtime_role.role_arn,
            description="IAM role ARN for AgentCore Runtime",
        )


# -- App entry point ---------------------------------------------------------

app = App()
AgenticTaxCalculatorStack(
    app,
    "AgenticTaxCalculatorStack",
    description="DynamoDB tables, IAM roles, and supporting resources for Agentic Tax Calculator",
)
app.synth()
