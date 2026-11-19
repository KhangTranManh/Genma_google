FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git bash && rm -rf /var/lib/apt/lists/*
COPY tools.py /opt/gemma/tools.py
WORKDIR /workspace
USER 1000:1000
CMD ["sleep", "infinity"]
