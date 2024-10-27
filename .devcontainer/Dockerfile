FROM mcr.microsoft.com/devcontainers/python:1-3.11

# Install build dependencies and tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    make \
    fd-find \
    ack-grep \
    curl \
    git \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && ln -s $(which fdfind) /usr/local/bin/fd \
    && ln -s $(which ack-grep) /usr/local/bin/ack \
    && rm -rf /var/lib/apt/lists/*

# Install pipx
RUN python -m pip install --user pipx
RUN python -m pipx ensurepath

# Install Poetry
RUN pipx install poetry

# Add pipx and poetry to PATH
ENV PATH="/root/.local/bin:$PATH"

# Verify installations
RUN pipx --version && poetry --version

# Set the working directory in the container
WORKDIR /workspace

#ARG GITHUB_TOKEN
#
## Fail if GITHUB_TOKEN is not set
#RUN if [ -z "$GITHUB_TOKEN" ]; then echo "Error: GITHUB_TOKEN is not set" && exit 1; fi
#
## Configure git to use the GITHUB_TOKEN
#RUN git config --global url."https://${GITHUB_TOKEN}:x-oauth-basic@github.com/".insteadOf "https://github.com/"

# Install Taskmates
ADD https://api.github.com/repos/taskmates/taskmates/git/refs/heads/main /tmp/taskmates-version.json
RUN pipx install --force --python 3.11 git+https://${GITHUB_TOKEN}@github.com/taskmates/taskmates.git

# Set up dev environment
ADD https://api.github.com/repos/taskmates/taskmates/git/refs/heads/main /tmp/repo-version.json
RUN git clone https://github.com/taskmates/taskmates.git .
RUN poetry install --no-interaction --no-ansi --quiet --no-root

# Command to run when starting the container
ENTRYPOINT ["bash"]
