FROM tiangolo/uwsgi-nginx-flask:python2.7
COPY app/requirements.txt /tmp/

# upgrade pip and install required python packages
RUN pip install -U pip
RUN pip install -r /tmp/requirements.txt
RUN python -m spacy download en_core_web_sm

# copy over our app code
COPY app /app
# RUN chown -R root:root /ml
# RUN chmod -R 777 /ml
# USER root
