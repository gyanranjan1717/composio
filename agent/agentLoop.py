"""The two-step conversation every agent in the pipeline uses.

Step 1: the model reads the web through tools until it stops asking for them.
Step 2: with those pages still in the conversation, it answers in a fixed JSON schema.
The steps are separate because the tool loop and a strict JSON output are configured
differently, and keeping them apart makes each one simple to reason about.
"""

import json

from google.genai import types

from composioToolbox import TOOL_DECLARATIONS
from geminiClient import ModelSession
from pipelineConfig import MAX_AGENT_TURNS


class AgentError(Exception):
    """The agent stopped without producing a usable answer."""


def runAgent(llmClient, toolbox, systemPrompt, task, answerRequest, answerSchema):
    """Return {answer, toolCalls, usage, hitTurnLimit, model}."""
    contents = [userText(task)]
    trace = {"toolCalls": [], "usage": {"inputTokens": 0, "outputTokens": 0}}
    modelSession = ModelSession(llmClient)
    hitTurnLimit = readWeb(modelSession, toolbox, systemPrompt, contents, trace)
    appendUserText(contents, answerRequest)
    answerConfig = types.GenerateContentConfig(
        system_instruction=systemPrompt,
        response_mime_type="application/json",
        response_json_schema=answerSchema,
    )
    response = modelSession.generate(contents, answerConfig)
    addUsage(trace["usage"], response.usage_metadata)
    if not response.text:
        raise AgentError("model returned no answer text")
    return {
        "answer": json.loads(response.text),
        "toolCalls": trace["toolCalls"],
        "usage": trace["usage"],
        "hitTurnLimit": hitTurnLimit,
        "model": modelSession.model,
    }


def readWeb(modelSession, toolbox, systemPrompt, contents, trace):
    """Run the tool loop, appending every turn to contents. Return True if the limit was hit."""
    config = types.GenerateContentConfig(
        system_instruction=systemPrompt,
        tools=[types.Tool(function_declarations=TOOL_DECLARATIONS)],
    )
    for _ in range(MAX_AGENT_TURNS):
        response = modelSession.generate(contents, config)
        addUsage(trace["usage"], response.usage_metadata)
        contents.append(extractModelContent(response))
        if not response.function_calls:
            return False
        contents.append(types.Content(role="user", parts=runTools(toolbox, response, trace)))
    return True


def extractModelContent(response):
    if not response.candidates or response.candidates[0].content is None:
        raise AgentError("model returned no content")
    return response.candidates[0].content


def runTools(toolbox, response, trace):
    parts = []
    for call in response.function_calls:
        arguments = dict(call.args or {})
        payload, failed = toolbox.run(call.name, arguments)
        trace["toolCalls"].append({"tool": call.name, "arguments": arguments, "failed": failed})
        parts.append(types.Part.from_function_response(name=call.name, response=payload))
    return parts


def userText(text):
    return types.Content(role="user", parts=[types.Part(text=text)])


def appendUserText(contents, text):
    """Add user text without creating two user turns in a row."""
    if contents[-1].role == "user":
        contents[-1].parts.append(types.Part(text=text))
        return
    contents.append(userText(text))


def addUsage(usageTotals, usageMetadata):
    usageTotals["inputTokens"] += usageMetadata.prompt_token_count or 0
    usageTotals["outputTokens"] += (usageMetadata.candidates_token_count or 0) + (
        usageMetadata.thoughts_token_count or 0
    )
