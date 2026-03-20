#!/bin/bash
# Auto-deploys skills with >= AUTO_APPROVE_CONFIDENCE% confidence
export AUTO_APPROVE_CONFIDENCE=${AUTO_APPROVE_CONFIDENCE:-95}
cd "$(dirname "$0")" && npm run evolve:once
