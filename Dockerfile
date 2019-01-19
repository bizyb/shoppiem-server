FROM tiangolo/uwsgi-nginx-flask:python2.7
COPY app/requirements.txt /tmp/

# upgrade pip and install required python packages
RUN pip install -U pip
RUN pip install -r /tmp/requirements.txt

# copy over our app code
COPY app /app
# RUN chown -R root:root /app
# RUN chmod 777 /app
# USER root
