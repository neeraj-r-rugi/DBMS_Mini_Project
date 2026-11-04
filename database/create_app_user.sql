CREATE DATABASE IF NOT EXISTS used_car_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'used_car_app'@'localhost'
  IDENTIFIED BY '314159';
CREATE USER IF NOT EXISTS 'used_car_app'@'127.0.0.1'
  IDENTIFIED BY '314159';

GRANT ALL PRIVILEGES ON used_car_db.* TO 'used_car_app'@'localhost';
GRANT ALL PRIVILEGES ON used_car_db.* TO 'used_car_app'@'127.0.0.1';
FLUSH PRIVILEGES;
