CREATE DATABASE IF NOT EXISTS used_car_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE used_car_db;

CREATE TABLE IF NOT EXISTS CAR (
    car_id VARCHAR(50) PRIMARY KEY,
    brand VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    year SMALLINT NOT NULL,
    fuel_type VARCHAR(30) NOT NULL,
    transmission VARCHAR(30) NOT NULL,
    km_driven INT UNSIGNED NOT NULL,
    purchase_price DECIMAL(12,2) NOT NULL,
    status ENUM('available','reserved','sold','archived') NOT NULL DEFAULT 'available',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CHECK (year BETWEEN 1900 AND 2100),
    CHECK (purchase_price >= 0)
);
CREATE TABLE IF NOT EXISTS OWNER (
    owner_id VARCHAR(50) PRIMARY KEY, name VARCHAR(100) NOT NULL,
    contact VARCHAR(50) NOT NULL, car_id VARCHAR(50) NOT NULL,
    FOREIGN KEY (car_id) REFERENCES CAR(car_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS APPRAISAL (
    appraisal_id VARCHAR(50) PRIMARY KEY, car_id VARCHAR(50) NOT NULL,
    appraisal_date DATE NOT NULL, predicted_price DECIMAL(12,2) NOT NULL,
    final_price DECIMAL(12,2), model_version VARCHAR(80),
    FOREIGN KEY (car_id) REFERENCES CAR(car_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS SERVICE_HISTORY (
    service_id VARCHAR(50) PRIMARY KEY, car_id VARCHAR(50) NOT NULL,
    service_date DATE NOT NULL, service_cost DECIMAL(10,2) NOT NULL,
    service_details TEXT NOT NULL,
    FOREIGN KEY (car_id) REFERENCES CAR(car_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS INSURANCE (
    insurance_id VARCHAR(50) PRIMARY KEY, car_id VARCHAR(50) NOT NULL,
    policy_number VARCHAR(100) NOT NULL UNIQUE, insurer VARCHAR(100) NOT NULL,
    policy_type VARCHAR(50) NOT NULL, start_date DATE NOT NULL,
    expiry_date DATE NOT NULL, FOREIGN KEY (car_id) REFERENCES CAR(car_id) ON DELETE CASCADE,
    CHECK (expiry_date >= start_date)
);
CREATE TABLE IF NOT EXISTS REGISTRATION (
    registration_id VARCHAR(50) PRIMARY KEY, car_id VARCHAR(50) NOT NULL UNIQUE,
    registration_number VARCHAR(50) NOT NULL UNIQUE, registration_date DATE NOT NULL,
    rto_code VARCHAR(20) NOT NULL, registration_state VARCHAR(50) NOT NULL,
    registration_type VARCHAR(50) NOT NULL, FOREIGN KEY (car_id) REFERENCES CAR(car_id) ON DELETE CASCADE
);

CREATE INDEX idx_car_brand_model ON CAR (brand, model);
CREATE INDEX idx_car_year ON CAR (year);
CREATE INDEX idx_car_status_price ON CAR (status, purchase_price);
CREATE INDEX idx_appraisal_car_date ON APPRAISAL (car_id, appraisal_date);
CREATE INDEX idx_service_car_date ON SERVICE_HISTORY (car_id, service_date);

CREATE OR REPLACE VIEW vw_car_inventory AS
SELECT c.car_id, c.brand, c.model, c.year, c.fuel_type, c.transmission,
       c.km_driven, c.purchase_price, c.status, o.name AS owner_name,
       o.contact AS owner_contact, r.registration_number,
       a.predicted_price AS latest_predicted_price
FROM CAR c
LEFT JOIN OWNER o ON o.car_id = c.car_id
LEFT JOIN REGISTRATION r ON r.car_id = c.car_id
LEFT JOIN APPRAISAL a ON a.appraisal_id = (
  SELECT a2.appraisal_id FROM APPRAISAL a2 WHERE a2.car_id = c.car_id
  ORDER BY a2.appraisal_date DESC, a2.appraisal_id DESC LIMIT 1
);

DELIMITER //
CREATE PROCEDURE sp_get_cars_by_budget(IN max_price DECIMAL(12,2))
BEGIN
  SELECT * FROM vw_car_inventory WHERE status = 'available'
  AND purchase_price <= max_price ORDER BY purchase_price ASC;
END//
CREATE FUNCTION fn_car_age(car_year SMALLINT) RETURNS INT DETERMINISTIC
BEGIN RETURN YEAR(CURDATE()) - car_year; END//
CREATE TRIGGER trg_car_validate_insert BEFORE INSERT ON CAR FOR EACH ROW
BEGIN
  IF NEW.purchase_price < 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Price must be non-negative';
  END IF;
END//
CREATE TRIGGER trg_car_default_appraisal AFTER INSERT ON CAR FOR EACH ROW
BEGIN
  INSERT INTO APPRAISAL (appraisal_id, car_id, appraisal_date, predicted_price, final_price, model_version)
  VALUES (CONCAT('AUTO_', NEW.car_id), NEW.car_id, CURRENT_DATE, NEW.purchase_price,
          NEW.purchase_price, 'inventory-initial');
END//
DELIMITER ;
