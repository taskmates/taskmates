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
RUN pipx install --force --python 3.11 poetry && pipx ensurepath

# Install Taskmates
ADD https://api.github.com/repos/taskmates/taskmates/git/refs/heads/main /tmp/taskmates-version.json
RUN pipx install --force --python 3.11 git+https://github.com/taskmates/taskmates.git

# Set up dev environment
WORKDIR /workspaces/taskmates

# Configure Poetry
RUN poetry config cache-dir /home/vscode/.cache/pypoetry
RUN poetry config virtualenvs.path /home/vscode/.cache/pypoetry/virtualenvs


# Install dependencies using Poetry
ADD https://raw.githubusercontent.com/taskmates/taskmates/main/pyproject.toml ./pyproject.toml
ADD https://raw.githubusercontent.com/taskmates/taskmates/main/poetry.lock ./poetry.lock
RUN poetry install --no-interaction --no-root
RUN rm pyproject.toml poetry.lock

# Now clone the full repository
ADD https://api.github.com/repos/taskmates/taskmates/git/refs/heads/main /tmp/repo-version.json
RUN git clone https://github.com/taskmates/taskmates.git .

RUN chown -R vscode:vscode .
USER vscode
