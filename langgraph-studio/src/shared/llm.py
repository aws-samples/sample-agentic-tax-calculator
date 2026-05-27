"""Shared Bedrock LLM instance for all agents.

Supports standard model IDs, cross-region inference profile IDs, and full
inference profile ARNs. Set TAX_CALC_LLM_MODEL_ID in .env to match
your account setup. See .env.example for options.
"""

import os
import boto3
from langchain_aws import ChatBedrockConverse

AWS_REGION = os.environ.get("AWS_REGION", "us-west-2")
MODEL_ID = os.environ.get("TAX_CALC_LLM_MODEL_ID", "anthropic.claude-sonnet-4-6-20250514")

bedrock_client = boto3.client("bedrock-runtime", region_name=AWS_REGION)

# ChatBedrockConverse accepts model IDs, inference profile IDs, and ARNs.
llm = ChatBedrockConverse(
    model=MODEL_ID,
    temperature=0,
    max_tokens=None,
    client=bedrock_client,
)
