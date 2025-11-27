# Test
##  create .env file in the root repository
### cann use the .env.example file as a template 
### varibles can be changed as per your requirements
DB_USERNAME=user
DB_PASSWORD=password
DB_HOST=db
DB_PORT=5432
DB_NAME=intraviewer_db
DATABASE_URL=postgresql://user:password@db:5432/intraviewer_db
SECRET_KEY=your-super-secret-jwt-key-here-32+chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

then run the following command
## to build and run the containers ##
    docker-compose up --build

## to run the containers in the background ##
    docker-compose up -d

## to stop the containers ##
    docker-compose down

## to stop the containers and remove the volumes ##
    docker-compose down -v

## to stop the containers and remove the volumes and networks ##
    docker-compose down --volumes --remove-orphans

## to stop the containers and remove the volumes and networks and images ##
    docker-compose down --volumes --remove-orphans --rmi all


   
   ## check url ##
   ##  for fast-api app
    http://localhost:8000
    http://localhost:8000/docs ## for api documentation

## for postgresql db
    http://localhost:5432

## for postgresql db admin
    http://localhost:5050
    default username: admin@admin.com
    default password: admin
    
     