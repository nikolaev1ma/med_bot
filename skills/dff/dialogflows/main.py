import logging

from emora_stdm import CompositeDialogueFlow, DialogueFlow
import time

import stdm.dialogflow_extention as dialogflow_extention

import dialogflows.flows.bot_persona as bot_persona_flow
import dialogflows.scopes as scopes

logger = logging.getLogger(__name__)


st_time = time.time()
composite_dialogflow = CompositeDialogueFlow(
    scopes.State.USR_ROOT,
    system_error_state=scopes.State.SYS_ERR,
    user_error_state=scopes.State.USR_ERR,
    initial_speaker=DialogueFlow.Speaker.USER,
)
up_time = time.time() - st_time
logger.info(f"dff start init exec time = {up_time:.3f}s")

composite_dialogflow.add_component(bot_persona_flow.dialogflow, scopes.BOT_PERSONA)

up_time = time.time() - st_time
logger.info(f"dff logic init dff exec time = {up_time:.3f}s")

dialogflow = composite_dialogflow.component(scopes.MAIN)
simplified_dialogflow = dialogflow_extention.DFEasyFilling(dialogflow=dialogflow)


##################################################################################################################
# bot_persona
##################################################################################################################


def bot_persona_request(ngrams, vars):
    flag = True
    logger.info(f"bot_persona_request={flag}")
    return flag


##################################################################################################################
##################################################################################################################
# linking
##################################################################################################################
##################################################################################################################

for node in [scopes.State.USR_ROOT, scopes.State.USR_ERR]:
    simplified_dialogflow.add_user_serial_transitions(
        node,
        {(scopes.BOT_PERSONA, bot_persona_flow.State.USR_START): bot_persona_request},
    )
simplified_dialogflow.set_error_successor(scopes.State.USR_ROOT, scopes.State.SYS_ERR)
simplified_dialogflow.set_error_successor(scopes.State.USR_ERR, scopes.State.SYS_ERR)
simplified_dialogflow.add_system_transition(
    scopes.State.SYS_ERR,
    scopes.State.USR_ROOT,
    bot_persona_flow.error_response,
)
composite_dialogflow.set_controller("SYSTEM")
composite_dialogflow._controller = simplified_dialogflow.get_dialogflow()
