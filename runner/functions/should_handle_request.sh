#!/bin/bash

# Function to check if the request should be handled
should_handle_request() {
  local recipient_role=$1
  local comment_user=$2

  # Parse Chat
  RECIPIENT=$(taskmates parse <"$MARKDOWN_CHAT_PATH" | jq -r ".messages[-1].recipient")
  RECIPIENT_ROLE=$(taskmates parse <"$MARKDOWN_CHAT_PATH" | jq -r ".messages[-1].recipient_role")

  echo "recipient=$RECIPIENT"
  echo "recipient_role=$RECIPIENT_ROLE"

  # Debug parsed chat
  echo "recipient_role = $RECIPIENT_ROLE"
  echo "login = $COMMENT_USER"

  # Check conditions
  if [ "$RECIPIENT_ROLE" == "assistant" ] && [ "$COMMENT_USER" == "srizzo" ]; then
    return 0 # True, should handle request
  else
    return 1 # False, should not handle request
  fi
}
