FROM apache/spark:3.5.1-python3

USER root

# Python deps needed by your Spark job
RUN pip install --no-cache-dir pandas psycopg2-binary pyarrow

# Create an app user with a real home
RUN useradd -m -u 1000 -s /bin/bash sparkuser || true

# Create writable dirs for Spark local + Ivy cache + checkpoints
RUN mkdir -p /tmp/spark /tmp/.ivy2 /opt/spark-checkpoints \
 && chown -R sparkuser:sparkuser /tmp /opt/spark-checkpoints \
 && chmod -R 775 /tmp /opt/spark-checkpoints

# Make Ivy cache absolute by default
ENV HOME=/tmp
ENV SPARK_LOCAL_DIRS=/tmp/spark
ENV SPARK_SUBMIT_OPTS="-Divy.cache.dir=/tmp/.ivy2 -Divy.home=/tmp/.ivy2"

USER sparkuser
