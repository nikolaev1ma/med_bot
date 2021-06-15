#!/usr/bin/env python

import logging
import numpy as np
import time

from flask import Flask, request, jsonify
from os import getenv
import sentry_sdk


sentry_sdk.init(getenv("SENTRY_DSN"))

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route("/respond", methods=["POST"])
def respond():
    st_time = time.time()

    dialogs = request.json["dialogs"]
    logger.info(f"\nlen!!!!!{len(dialogs)}\n")
    response_candidates = []
    #response_candidates = [dialog["utterances"][-1]["hypotheses"] for dialog in dialogs]
    for dialog in dialogs:
        for utt in dialog["utterances"]:
            try:
                response_candidates.append(utt["hypotheses"])
            except:
                pass
    logger.info(response_candidates)
    #logger.info(f"\nresponse!!!!!{response_candidates}\n")

    selected_skill_names = []
    selected_responses = []
    selected_confidences = []
    selected_human_attributes = []
    selected_bot_attributes = []

    for res in response_candidates:
        try:
            res = res[0]
            if res["skill_name"] == "dff_bot_persona_skill":
                selected_confidences.append(res["confidence"])
                selected_skill_names.append(res["skill_name"])
                selected_responses.append(res["text"])
                selected_human_attributes.append(res.get("human_attributes", {}))
                selected_bot_attributes.append(res.get("bot_attributes", {}))
        except:
            pass

    total_time = time.time() - st_time
    logger.info(f"rule_based_response_selector exec time = {total_time:.3f}s")
    return jsonify(list(zip(selected_skill_names, selected_responses, selected_confidences, selected_human_attributes, selected_bot_attributes)))


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=3000)
