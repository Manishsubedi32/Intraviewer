Order Phase Method Endpoint Description
1 Auth POST /auth/signup Register a new user.
2 Auth POST /auth/login Login to receive Access & Refresh tokens.
3 Auth POST /auth/refresh Get a new Access token using a Refresh token.
4 Setup POST /userinput/data Upload CV (PDF) and Job Description to get IDs.
5 Setup GET /userinput/cvs (Optional) List previously uploaded CVs. (not created)
6 Interview POST /sessions/start Initialize a session using cv_id and prompt_id.
7 Interview WS /sessions/ws/{session_id} WebSocket: Live audio streaming, AI questions, & transcription.
8 Interview POST /sessions/end/{session_id} Manually terminate the session (if not done via WS).
9 Dashboard GET /sessions/history List all past interviews with status and scores. {nocreated}
10 Review GET /sessions/{session_id}/analysis Get final AI feedback, score, and summary.
11 Review GET | /sessions/{session_id}/transcript | Get the full text transcript of the conversation. |
12 Review GET /questions/{session_id} Get the specific list of questions generated for this session.
13.sessions/delete/{session_id}
14.User delete /user/delete/{user_id} to delete user(have to be admin)
