"""Gemini access with model fallback for the free tier.

Free-tier Gemini often answers 503/504/429 on the stronger models. A ModelSession starts on
the first model in MODEL_PREFERENCE and, when that model is unavailable, moves to the next
one and stays there for the rest of that app, so one app is never researched by a mix of
models halfway through a conversation more than necessary.
"""

import os
import time

import httpx
from google import genai
from google.genai import errors, types

from pipelineConfig import (
    MODEL_PREFERENCE,
    RATE_LIMIT_RETRY_DELAYS_SECONDS,
    REQUEST_TIMEOUT_MILLISECONDS,
)

RETRYABLE_STATUS_CODES = (429, 500, 503, 504)
SINGLE_ATTEMPT = 1
# After a model is found overloaded, later apps skip it for this long instead of each one
# paying for a failed attempt (a 504 costs the full request timeout).
MODEL_COOLDOWN_SECONDS = 600
modelCooldownEnds = {}


class ModelSession:
    def __init__(self, llmClient):
        self.llmClient = llmClient
        self.modelIndex = firstAvailableModelIndex()

    @property
    def model(self):
        return MODEL_PREFERENCE[self.modelIndex]

    def generate(self, contents, config):
        """Call the current model; on overload fall to the next model, then wait and retry."""
        while self.modelIndex < len(MODEL_PREFERENCE) - 1:
            try:
                return self.requestOnce(contents, config)
            except (errors.APIError, httpx.TimeoutException) as error:
                if not isRetryable(error):
                    raise
                modelCooldownEnds[self.model] = time.time() + MODEL_COOLDOWN_SECONDS
                self.modelIndex += 1
        return self.requestLastModel(contents, config)

    def requestLastModel(self, contents, config):
        for delaySeconds in RATE_LIMIT_RETRY_DELAYS_SECONDS:
            try:
                return self.requestOnce(contents, config)
            except (errors.APIError, httpx.TimeoutException) as error:
                if not isRetryable(error):
                    raise
                time.sleep(delaySeconds)
        return self.requestOnce(contents, config)

    def requestOnce(self, contents, config):
        return self.llmClient.models.generate_content(
            model=self.model, contents=contents, config=config
        )


def buildLlmClient():
    return genai.Client(
        api_key=os.environ["GEMINI_API_KEY"],
        http_options=types.HttpOptions(
            timeout=REQUEST_TIMEOUT_MILLISECONDS,
            retry_options=types.HttpRetryOptions(attempts=SINGLE_ATTEMPT),
        ),
    )


def firstAvailableModelIndex():
    now = time.time()
    for index, model in enumerate(MODEL_PREFERENCE[:-1]):
        if modelCooldownEnds.get(model, 0) <= now:
            return index
    return len(MODEL_PREFERENCE) - 1


def isRetryable(error):
    if isinstance(error, httpx.TimeoutException):
        return True
    return error.code in RETRYABLE_STATUS_CODES
