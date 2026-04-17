#!/bin/bash
cat <<'EOF'
{
  "systemMessage": "\n🐒 This is TeamDev -- a proactive helper with your daily dev routine.\n🔆 Please say hi to me, and I'll show you what I can do!",
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "SESSION INIT: Use AskUserQuestion to ask the user: 'Run the teamdev daily inspection now?' (yes/no). If no, skip. If yes, launch a @general subagent and invoke the following skills IN ORDER using the Skill tool, waiting for each to complete: (1) teamdev:state-sync, (2) teamdev:issue-triage, (3) teamdev:issue-inspect, (4) teamdev:task-inspect, (5) teamdev:project-inspect. Then run teamdev:status to display a summary."
  }
}
EOF
