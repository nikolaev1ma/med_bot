# %%
import json
import logging
import os
import random
import re

import requests
import subprocess

from enum import Enum, auto

import sentry_sdk
from spacy import load

import stdm.dialogflow_extention as dialogflow_extention
import utils.state as state_utils
import utils.condition as condition_utils
import dialogflows.scopes as scopes
from constants import CAN_NOT_CONTINUE, CAN_CONTINUE_SCENARIO, CAN_CONTINUE_SCENARIO_DONE, MUST_CONTINUE

import requests

sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"))

logger = logging.getLogger(__name__)

spacy_nlp = load("en_core_web_sm")

# global vars ##########################
PROGRAM_STARTED = 0
SYMPTOMS = ""
NOT_MED_ANSWERS = 0
MAX_CORRECTING = 10
CORRECTION_INDEX = 0
CURRENT_MED_ANSWER = {}


########################################
def startted_program():
    PROGRAM_STARTED = 1


def symptoms_get():
    SYMPTOMS = ""


startted_program()
symptoms_get()

with open("topic_favorites.json", "r") as f:
    FAV_STORIES_TOPICS = json.load(f)
your_favorite_request_re = re.compile("(you|your|yours|you have a).*(favorite|favourite|like)", re.IGNORECASE)

CONF_HIGH = 1.0
CONF_MIDDLE = 0.95
CONF_LOW = 0.9


class State(Enum):
    USR_START = auto()

    SYS_GREETING = auto()
    USR_ANSWER = auto()

    MED_CHOICE = auto()

    SYS_NOT_MED_ANSWER = auto()
    SYS_NOT_DOUBLE_MED_ANSWER = auto()
    SYS_GOOD_MED_ANSEWR = auto()
    USR_CORRECTION = auto()
    SYS_REPLACE = auto()
    SYS_NOT_GOOD_MED_ASWER = auto()

    SYS_TMP = auto()
    USR_TMP = auto()

    SYS_ERR = auto()
    USR_ERR = auto()


# %%

##################################################################################################################
# Init DialogFlow
##################################################################################################################

simplified_dialogflow = dialogflow_extention.DFEasyFilling(State.USR_START)


##################################################################################################################
##################################################################################################################
# Design DialogFlow.
##################################################################################################################
##################################################################################################################
##################################################################################################################
# yes
##################################################################################################################


def yes_request(str_i):
    str_ = str_i.lower()
    logger.info(f"СТРОКА: {str_}")
    if 'yes' in str_ \
            or 'да' in str_ \
            or 'of course' in str_ \
            or 'конечно' in str_:
        return True
    return False


##################################################################################################################
# no
##################################################################################################################


def no_request(ngrams, vars):
    flag = condition_utils.is_no_vars(vars)
    logger.info(f"no_request {flag}")
    return flag


##################################################################################################################
# error
##################################################################################################################


def error_response(vars):
    logger.info(vars)
    state_utils.set_confidence(vars, 0)
    global SYMPTOMS
    global NOT_MED_ANSWERS
    global CORRECTION_INDEX
    global CURRENT_MED_ANSWER
    SYMPTOMS = ""
    NOT_MED_ANSWERS = 0
    CORRECTION_INDEX = 0
    CURRENT_MED_ANSWER = {}
    return "Sorry"


##################################################################################################################
# edges
##################################################################################################################

def started(ngrams, vars):
    utt = state_utils.get_last_human_utterance(vars)["text"].lower()

    flag = len(utt) > 0 or PROGRAM_STARTED
    logger.info(f"started_request {flag}")
    return flag


def started_quesstion(vars):
    try:
        utt = state_utils.get_last_human_utterance(vars)["text"].lower()

        response = u"Приветствую! Могли бы вы четко описать что вас беспокоит?"
        state_utils.set_confidence(vars, confidence=CONF_HIGH)
        state_utils.set_can_continue(vars, continue_flag=CAN_CONTINUE_SCENARIO)

        return response
    except Exception as exc:
        logger.info("WTF in secret_caught_response")
        logger.exception(exc)
        state_utils.set_confidence(vars, 0)

        return error_response(vars)


def med_first_answer(vars):
    utt = state_utils.get_last_human_utterance(vars)["text"].lower()

    logger.info(f"НАЧАЛО ЗАПРОСА")
    # 45.89.225.193
    """
    json_file = subprocess.call(['curl', '-x', 'post',
                                 '"http://45.89.225.193:50002/predict_symptoms_and_questions?text={}&choiced_symptoms={}"'.format(
                                     utt, SYMPTOMS),
                                 '-H', '"accept: application/json"',
                                 '-d', '""'])
    """
    response = requests.post('http://45.89.225.193:50002/predict_symptoms_and_questions',
                             data={
                                 'text': utt,
                                 'choiced_symptoms': SYMPTOMS})
    json_file = response.json()

    logger.info(f"ПРИШЕЛ ОТВЕТ: {json_file}")
    return json_file


def not_med_answer(ngrams, vars):
    med_res = med_first_answer(vars)
    global NOT_MED_ANSWERS
    if not med_res['is_med_text'] and NOT_MED_ANSWERS == 0:
        NOT_MED_ANSWERS += 1
        return True
    return False


def double_not_med_answer(ngrams, vars):
    med_res = med_first_answer(vars)
    global NOT_MED_ANSWERS
    if not med_res['is_med_text'] and NOT_MED_ANSWERS == 1:
        NOT_MED_ANSWERS += 1
        return True
    return False


def not_good_med_answer(ngrams, vars):
    med_res = med_first_answer(vars)
    global CURRENT_MED_ANSWER
    global NOT_MED_ANSWERS
    if med_res['is_med_text'] and not med_res['is_possible_predict_diagnosis']:
        CURRENT_MED_ANSWER = med_res
        return True
    return False


def good_med_answer(ngrams, vars):
    med_res = med_first_answer(vars)
    global NOT_MED_ANSWERS
    if med_res['is_med_text'] and med_res['is_possible_predict_diagnosis']:
        return True
    return False


def bad_finish(vars):
    try:
        utt = state_utils.get_last_human_utterance(vars)["text"]

        state_utils.set_confidence(vars, confidence=CONF_HIGH)
        state_utils.set_can_continue(vars, continue_flag=CAN_NOT_CONTINUE)

        response = "Извините, я вас совсем не понимаю, до свидания!"
        global SYMPTOMS
        global NOT_MED_ANSWERS
        global CORRECTION_INDEX
        global CURRENT_MED_ANSWER
        SYMPTOMS = ""
        NOT_MED_ANSWERS = 0
        CORRECTION_INDEX = 0
        CURRENT_MED_ANSWER = {}
        return response

    except Exception as exc:
        logger.info("WTF in bad_finish")
        logger.exception(exc)
        state_utils.set_confidence(vars, 0)

        return error_response(vars)


def replace(vars):
    try:
        utt = state_utils.get_last_human_utterance(vars)["text"]

        state_utils.set_confidence(vars, confidence=CONF_HIGH)
        state_utils.set_can_continue(vars, continue_flag=CAN_NOT_CONTINUE)

        response = "Извините, я вас не понимаю, пожалуйста, скажите четко что вас беспокоит?"
        global CORRECTION_INDEX
        global CURRENT_MED_ANSWER
        CORRECTION_INDEX = 0
        CURRENT_MED_ANSWER = {}
        return response

    except Exception as exc:
        logger.info("WTF in replace")
        logger.exception(exc)
        state_utils.set_confidence(vars, 0)

        return error_response(vars)


def correction(vars):
    try:
        global CURRENT_MED_ANSWER
        utt = state_utils.get_last_human_utterance(vars)["text"]

        state_utils.set_confidence(vars, confidence=CONF_HIGH)
        state_utils.set_can_continue(vars, continue_flag=CAN_NOT_CONTINUE)

        qustion_list = CURRENT_MED_ANSWER['symptoms_and_questions']
        quest = ""
        if CORRECTION_INDEX < MAX_CORRECTING and CORRECTION_INDEX < len(qustion_list):
            q = qustion_list[CORRECTION_INDEX]
            symbol = q[0]
            quest = q[1]

        return quest

    except Exception as exc:
        logger.info("WTF in correction")
        logger.exception(exc)
        state_utils.set_confidence(vars, 0)

        return error_response(vars)


def correction_continue(ngrams, vars):
    try:
        global CURRENT_MED_ANSWER
        qustion_list = CURRENT_MED_ANSWER['symptoms_and_questions']
        global CORRECTION_INDEX
        global SYMPTOMS
        if CORRECTION_INDEX + 1 < MAX_CORRECTING and CORRECTION_INDEX + 1 < len(qustion_list):
            utt = state_utils.get_last_human_utterance(vars)["text"]
            logger.info(f"НЕПОСЛЕДНИЙ ВЫБРОМ")
            logger.info(qustion_list[CORRECTION_INDEX])
            if yes_request(utt):
                q = qustion_list[CORRECTION_INDEX]
                symbol = q[0]
                SYMPTOMS += ',' + symbol
            CORRECTION_INDEX += 1
            return True
        return False
    except:
        return False


def finish_correction(ngrams, vars):
    try:
        global CURRENT_MED_ANSWER
        qustion_list = CURRENT_MED_ANSWER['symptoms_and_questions']
        global CORRECTION_INDEX
        global SYMPTOMS
        if CORRECTION_INDEX + 1 == MAX_CORRECTING or CORRECTION_INDEX + 1 == len(qustion_list):

            utt = state_utils.get_last_human_utterance(vars)["text"]
            logger.info(f"ПОСЛЕДНИЙ ВЫБРОМ")
            logger.info(qustion_list[CORRECTION_INDEX])

            if yes_request(utt):
                q = qustion_list[CORRECTION_INDEX]
                symbol = q[0]
                SYMPTOMS += ',' + symbol
            CORRECTION_INDEX += 1
            return True
        return False
    except:
        return False


def finish_result(vars):
    try:
        global SYMPTOMS
        utt = state_utils.get_last_human_utterance(vars)["text"]

        state_utils.set_confidence(vars, confidence=CONF_HIGH)
        state_utils.set_can_continue(vars, continue_flag=CAN_NOT_CONTINUE)
        """
        json_file = subprocess.call(['curl', '-x', 'post',
                                     '"http://45.89.225.193:50002/predict_diagnosis?text={}&choiced_symptoms={}"'.format(
                                         utt, SYMPTOMS),
                                     '-H', '"accept: application/json"',
                                     '-d', '""'])
        """

        response = requests.post('http://45.89.225.193:50002/predict_diagnosis',
                                 data={
                                     'text': utt,
                                     'choiced_symptoms': SYMPTOMS})
        json_file = response.json()

        diagnosis = json_file['diagnosis']
        logger.info(f"ДИАГНОЗ {diagnosis}")
        result = ""
        for doctor in diagnosis:
            result += doctor
            result += "."
            diskription = diagnosis[doctor]
            result += "Занимается "
            for good_at in diskription['diseases']:
                result += good_at + ", "
            result += "можно найти на " + diskription['link'] + ".\n"
        global NOT_MED_ANSWERS
        global CORRECTION_INDEX
        global CURRENT_MED_ANSWER
        SYMPTOMS = ""
        NOT_MED_ANSWERS = 0
        CORRECTION_INDEX = 0
        CURRENT_MED_ANSWER = {}
        return result

    except Exception as exc:
        logger.info("WTF in correction")
        logger.exception(exc)
        state_utils.set_confidence(vars, 0)

        return error_response(vars)


def tmp_func(ngrams, vars):
    utt = state_utils.get_last_human_utterance(vars)["text"].lower()

    flag = len(utt) > 0 or PROGRAM_STARTED
    logger.info(f"TMP!!!! request {flag}")
    return flag


def tmp_user_ansewr(vars):
    request = "YES, I AM IN TMP NODE"

    state_utils.set_confidence(vars, confidence=CONF_HIGH)
    state_utils.set_can_continue(vars, continue_flag=CAN_CONTINUE_SCENARIO)
    return request


def good_replace(vars):
    try:
        utt = state_utils.get_last_human_utterance(vars)["text"]

        state_utils.set_confidence(vars, confidence=CONF_HIGH)
        state_utils.set_can_continue(vars, continue_flag=CAN_NOT_CONTINUE)

        response = "Хорошо! А теперь можете повторить что вас беспокоит в подробной форме?"
        global CORRECTION_INDEX
        global CURRENT_MED_ANSWER
        CORRECTION_INDEX = 0
        CURRENT_MED_ANSWER = {}
        return response

    except Exception as exc:
        logger.info("WTF in replace")
        logger.exception(exc)
        state_utils.set_confidence(vars, 0)

        return error_response(vars)
##################################################################################################################
##################################################################################################################
# linking
##################################################################################################################
##################################################################################################################


##################################################################################################################
#  START


simplified_dialogflow.add_user_transition(State.USR_START, State.SYS_GREETING, started)
simplified_dialogflow.set_error_successor(State.USR_START, State.SYS_ERR)

simplified_dialogflow.add_system_transition(State.SYS_GREETING, State.USR_ANSWER, started_quesstion)
simplified_dialogflow.set_error_successor(State.SYS_GREETING, State.SYS_ERR)

simplified_dialogflow.add_user_serial_transitions(
    State.USR_ANSWER,
    {
        State.SYS_NOT_MED_ANSWER: not_med_answer,
        State.SYS_NOT_DOUBLE_MED_ANSWER: double_not_med_answer,
        State.SYS_NOT_GOOD_MED_ASWER: not_good_med_answer,
        State.SYS_GOOD_MED_ANSEWR: good_med_answer,
    },
)

simplified_dialogflow.set_error_successor(State.USR_ANSWER, State.SYS_ERR)

'''
simplified_dialogflow.add_user_transition(State.USR_ANSWER, State.SYS_TMP, tmp_func)

simplified_dialogflow.add_system_transition(State.SYS_TMP, State.USR_TMP, tmp_user_ansewr)
simplified_dialogflow.set_error_successor(State.SYS_TMP, State.SYS_ERR)
'''

simplified_dialogflow.add_system_transition(State.SYS_NOT_DOUBLE_MED_ANSWER, State.USR_START, bad_finish)
simplified_dialogflow.set_error_successor(State.SYS_NOT_DOUBLE_MED_ANSWER, State.SYS_ERR)

simplified_dialogflow.add_system_transition(State.SYS_NOT_MED_ANSWER, State.USR_ANSWER, replace)
simplified_dialogflow.set_error_successor(State.SYS_NOT_MED_ANSWER, State.SYS_ERR)

simplified_dialogflow.add_system_transition(State.SYS_NOT_GOOD_MED_ASWER, State.USR_CORRECTION, correction)
simplified_dialogflow.set_error_successor(State.SYS_NOT_GOOD_MED_ASWER, State.SYS_ERR)

simplified_dialogflow.add_user_serial_transitions(
    State.USR_CORRECTION,
    {
        State.SYS_NOT_GOOD_MED_ASWER: correction_continue,
        State.SYS_REPLACE: finish_correction,
    },
)
simplified_dialogflow.set_error_successor(State.USR_CORRECTION, State.SYS_ERR)

simplified_dialogflow.add_system_transition(State.SYS_REPLACE, State.USR_ANSWER, good_replace)
simplified_dialogflow.set_error_successor(State.SYS_REPLACE, State.SYS_ERR)

simplified_dialogflow.add_system_transition(State.SYS_GOOD_MED_ANSEWR, State.USR_START, finish_result)
simplified_dialogflow.set_error_successor(State.SYS_GOOD_MED_ANSEWR, State.SYS_ERR)

#################################################################################################################
#  SYS_ERR
simplified_dialogflow.add_system_transition(
    State.SYS_ERR,
    (scopes.MAIN, scopes.State.USR_ROOT),
    error_response,
)
dialogflow = simplified_dialogflow.get_dialogflow()
