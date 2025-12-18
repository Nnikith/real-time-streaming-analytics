FROM apache/spark:3.5.1-python3

USER root

# Python deps needed by your Spark job
RUN pip install --no-cache-dir pandas psycopg2-binary pyarrow

# optional: if you ever use these libs
# RUN pip install --no-cache-dir pyarrow

USER root
