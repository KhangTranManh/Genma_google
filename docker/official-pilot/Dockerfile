FROM python:3.13-slim
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends git patch && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /opt/pilot/requirements.txt
RUN pip install --no-cache-dir -r /opt/pilot/requirements.txt
RUN git config --global user.email agent@eval && git config --global user.name Agent && git config --global init.defaultBranch main
ENV TEST_TMPDIR=/tmp SETUPTOOLS_SCM_PRETEND_VERSION=99.0.0 PIP_NO_INDEX=1
WORKDIR /workspace
