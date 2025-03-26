docker run --name shopsmart \
  -e MYSQL_ROOT_PASSWORD=root_password \
  -e MYSQL_DATABASE=commerce \
  -e MYSQL_USER=admin \
  -e MYSQL_PASSWORD=asdfghjkl \
  -p 3306:3306 \
  -d mysql:8.0