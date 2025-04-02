#!/bin/bash

# Get the current branch name
BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Check if there are changes to commit
if [[ -n $(git status --porcelain) ]]; then
    echo "Changes detected. Please enter a commit message:"
    read COMMIT_MSG
    
    # If the message is empty, exit
    if [[ -z "$COMMIT_MSG" ]]; then
        echo "Commit message cannot be empty. Aborting."
        exit 1
    fi

    # Add changes, commit, and push
    git add .
    git commit -m "$COMMIT_MSG"
    git push origin "$BRANCH"
    
    echo "Changes pushed to $BRANCH branch successfully!"
else
    echo "Nothing to commit on $BRANCH branch."
fi
