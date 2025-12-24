TO check db connection use : GET /db/debug

Authentication
Defined in auth.py (Prefix: /auth)

POST /auth/signup
POST /auth/login
POST /auth/refresh

Users
GET /users/me
POST /users/me/password --> to change password

Questions

GET /questions/all

POST /questions/add --> only admin has the access

POST /userinput/data --> frontend can store cv and prompt ani api will send back cvid ra promptid

POST /sessions/start --> aba tyo mathi ko data pathaunu paryo yeta
