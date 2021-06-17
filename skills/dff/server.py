#!/usr/bin/env python

import logging
import time
import os
import random
import re

from flask import Flask, request, jsonify
from healthcheck import HealthCheck
import sentry_sdk
from sentry_sdk.integrations.logging import ignore_logger

#import program_y.text_preprocessing as text_utils
import utils.dialogflow as dialogflow_utils
import dialogflows.main as main_dialogflow
# import test_server



spaces_pat = re.compile(r"\s+")
special_symb_pat = re.compile(r"[^a-zа-я0-9 ]", re.IGNORECASE)



ignore_logger("root")

sentry_sdk.init(os.getenv("SENTRY_DSN"))
SERVICE_NAME = "dff_bot_persona_skill"
SERVICE_PORT = 8105
RANDOM_SEED = int(os.getenv("RANDOM_SEED", 2718))

logging.basicConfig(format="%(asctime)s - %(pathname)s - %(lineno)d - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


app = Flask(__name__)
health = HealthCheck(app, "/healthcheck")

DF = main_dialogflow.composite_dialogflow

def clean_text(text):
    return special_symb_pat.sub("", spaces_pat.sub(" ", text.lower())).strip()

def handler(requested_data, random_seed=None):
    st_time = time.time()
    dialog_batch = requested_data.get("dialog_batch", [])
    human_utter_index_batch = requested_data.get("human_utter_index_batch", [0] * len(dialog_batch))
    state_batch = requested_data.get(f"{SERVICE_NAME}_state_batch", [{}] * len(dialog_batch))
    logger.info(f"STATE_BATCH = {state_batch}")
    entities_batch = requested_data.get("entities_batch", [{}] * len(dialog_batch))
    used_links_batch = requested_data.get("used_links_batch", [{}] * len(dialog_batch))
    disliked_skills_batch = requested_data.get("disliked_skills_batch", [{}] * len(dialog_batch))
    random_seed = requested_data.get("random_seed", random_seed)  # for tests

    responses = []
    for human_utter_index, dialog, state, entities, used_links, disliked_skills in zip(
        human_utter_index_batch, dialog_batch, state_batch, entities_batch, used_links_batch, disliked_skills_batch
    ):
        try:
            # for tests
            if random_seed:
                random.seed(int(random_seed))

            text = dialog["human_utterances"][-1]["text"]
            text = clean_text(text)

            dialogflow_utils.load_into_dialogflow(
                DF, human_utter_index, dialog, state, entities, used_links, disliked_skills
            )
            text, confidence, can_continue = dialogflow_utils.run_turn(DF, text)
            logger.info(f"text: {text}")
            state, used_links, disliked_skills = dialogflow_utils.get_dialog_state(DF)

            human_attr = {f"{SERVICE_NAME}_state": state, "used_links": used_links, "disliked_skills": disliked_skills}
            logger.info(f"HUMAN_ATTR = {human_attr}")
            hype_attr = {"can_continue": can_continue}

            responses.append((text, confidence, human_attr, {}, hype_attr))
        except Exception as exc:
            sentry_sdk.capture_exception(exc)
            logger.exception(exc)
            responses.append(("", 0.0, {}, {}, {}))

        total_time = time.time() - st_time
        logger.info(f"{SERVICE_NAME} exec time = {total_time:.3f}s")
    return responses


try:
    # test_server.run_test(handler)
    logger.info("test query processed")
except Exception as exc:
    sentry_sdk.capture_exception(exc)
    logger.exception(exc)
    raise exc

logger.info(f"{SERVICE_NAME} is loaded and ready")


@app.route("/respond", methods=["POST"])
def respond():
    # import common.test_utils as t_utils; t_utils.save_to_test(request.json,"tests/lets_talk_in.json",indent=4)  # TEST
    # responses = handler(request.json, RANDOM_SEED)  # TEST
    # import common.test_utils as t_utils; t_utils.save_to_test(responses,"tests/lets_talk_out.json",indent=4)  # TEST
    responses = handler(request.json)
    logger.info(responses)
    return jsonify(responses)


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=SERVICE_PORT)
