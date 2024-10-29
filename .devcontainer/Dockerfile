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

# Add pipx and poetry to PATH
#ENV PATH="/home/$USERNAME/.local/bin:$PATH"

# Verify installations
RUN pipx --version && poetry --version

# Set the working directory in the container
WORKDIR /workspace

# Install Taskmates
ADD https://api.github.com/repos/taskmates/taskmates/git/refs/heads/main /tmp/taskmates-version.json
RUN pipx install --force --python 3.11 git+https://github.com/taskmates/taskmates.git

# Set up dev environment
ADD https://api.github.com/repos/taskmates/taskmates/git/refs/heads/main /tmp/repo-version.json
RUN git clone https://github.com/taskmates/taskmates.git .

# Install dependencies using Poetry with cache mount
RUN --mount=type=cache,target=/root/.cache/pypoetry,id=poetry_cache \
    poetry install --no-interaction --no-root
