from fastapi import FastAPI
import requests

# import httpx
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from composio import Composio
from openai import OpenAI

import webbrowser

app = FastAPI()


class IntegrationParams(BaseModel):
    composioApiKey: str


class ExecutionParams(BaseModel):
    composio: str
    integration: str
    openai: str
    prompt: str


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"status": 200, "message": "Server running."}


@app.post("/integrations/")
async def integrations(params: IntegrationParams):
    url = "https://backend.composio.dev/api/v1/integrations"
    headers = {"X-API-Key": params.composioApiKey}
    response = requests.request("GET", url, headers=headers)
    return response.json()



@app.post("/execute/")
async def execute(params: ExecutionParams):
    try:
        client = Composio(params.composio)

        # client.get_integration(**YourIntegrationID**)
        integration = client.get_integration(params.integration)

        # Trying to initiate a new connection
        connected_account = integration.initiate_connection(entity_id=None)

        print("Complete the auth flow, link: ", connected_account.redirectUrl)

        webbrowser.open(connected_account.redirectUrl)

        # Keep Polling and wait until timeout
        connected_account = connected_account.wait_until_active(timeout=60)
        print(connected_account)

        actions = connected_account.get_all_actions()

        task = params.prompt

        # Initialize the OpenAI client with your API key
        openai_client = OpenAI(api_key=params.openai)

        # Create a chat completion request to decide on the action
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            tools=actions,  # Passing actions we fetched earlier.
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": task},
            ],
        )

        # Execute Function calls
        execution_details = connected_account.handle_tools_calls(response)

        return {"status": "200", "message": execution_details}

    except Exception as e:
        return {"status": "404", "message": str(e)}
