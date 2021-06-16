FROM python:3.9.1
# ###################### IMMUTABLE SECTION ######################################
# Do not change anything in this section 
WORKDIR /src

COPY requirements.txt .
RUN pip install -r requirements.txt

RUN python -m spacy download en
RUN python -m spacy download en_core_web_sm
RUN python -m spacy download en_core_web_md
RUN python -m nltk.downloader vader_lexicon
RUN python -m nltk.downloader all


COPY /. /.
COPY constants.py constants.py
COPY server.py server.py
COPY topic_favorites.json topic_favorites.json
RUN bash /scripts/programy_logger_off.sh

# ###################### CUSTOM SECTION ######################################
# Here you can make changes 
COPY ./ ./

# wait for a server answer ( INTERVAL + TIMEOUT ) * RETRIES seconds after that change stutus to unhealthy
HEALTHCHECK --interval=5s --timeout=5s --retries=3 CMD curl --fail 127.0.0.1:8105/healthcheck || exit 1


CMD gunicorn --workers=1 server:app -b 0.0.0.0:8105

