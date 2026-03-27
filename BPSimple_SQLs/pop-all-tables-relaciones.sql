-- Customers
INSERT INTO customer(title, fname, lname, addressline, town, zipcode, phone) VALUES
('Miss', 'Jenny', 'Stones', '27 Rowan Avenue', 'Hightown', 'NT2 1AQ', '023 9876'),
('Mr', 'Andrew', 'Stones', '52 The Willows', 'Lowtown', 'LT5 7RA', '876 3527'),
('Miss', 'Alex', 'Matthew', '4 The Street', 'Nicetown', 'NT2 2TX', '010 4567'),
('Mr', 'Adrian', 'Matthew', 'The Barn', 'Yuleville', 'YV67 2WR', '487 3871'),
('Mr', 'Simon', 'Cozens', '7 Shady Lane', 'Oakenham', 'OA3 6QW', '514 5926'),
('Mr', 'Neil', 'Matthew', '5 Pasture Lane', 'Nicetown', 'NT3 7RT', '267 1232'),
('Mr', 'Richard', 'Stones', '34 Holly Way', 'Bingham', 'BG4 2WE', '342 5982'),
('Mrs', 'Ann', 'Stones', '34 Holly Way', 'Bingham', 'BG4 2WE', '342 5982'),
('Mrs', 'Christine', 'Hickman', '36 Queen Street', 'Histon', 'HT3 5EM', '342 5432'),
('Mr', 'Mike', 'Howard', '86 Dysart Street', 'Tibsville', 'TB3 7FG', '505 5482'),
('Mr', 'Dave', 'Jones', '54 Vale Rise', 'Bingham', 'BG3 8GD', '342 8264'),
('Mr', 'Richard', 'Neill', '42 Thatched Way', 'Winnersby', 'WB3 6GQ', '505 6482'),
('Mrs', 'Laura', 'Hardy', '73 Margarita Way', 'Oxbridge', 'OX2 3HX', '821 2335'),
('Mr', 'Bill', 'O''Neill', '2 Beamer Street', 'Welltown', 'WT3 8GM', '435 1234'),
('Mr', 'David', 'Hudson', '4 The Square', 'Milltown', 'MT2 6RT', '961 4526'),
('Mr', 'Jules', 'Hamilton', '97 The Square', 'Manchester', 'MCH1 6TS', NULL);

-- Items
INSERT INTO item(description, cost_price, sell_price) VALUES
('Wood Puzzle', 15.23, 21.95),
('Rubik Cube', 7.45, 11.49),
('Linux CD', 1.99, 2.49),
('Tissues', 2.11, 3.99),
('Picture Frame', 7.54, 9.95),
('Fan Small', 9.23, 15.75),
('Fan Large', 13.36, 19.95),
('Toothbrush', 0.75, 1.45),
('Roman Coin', 2.34, 2.45),
('Carrier Bag', 0.01, 0.0),
('Speakers', 19.73, 25.32);

-- Barcodes
INSERT INTO barcode(barcode_ean, item_id) VALUES
('6241527836173', 1),
('6241574635234', 2),
('6264537836173', 3),
('6241527746363', 3),
('7465743843764', 4),
('3453458677628', 5),
('6434564564544', 6),
('8476736836876', 7),
('6241234586487', 8),
('9473625532534', 8),
('9473627464543', 8),
('4587263646878', 9),
('9879879837489', 11),
('2239872376872', 11);

-- Stock
INSERT INTO stock(item_id, quantity) VALUES
(1, 12),
(2, 2),
(4, 8),
(5, 3),
(7, 8),
(8, 18),
(10, 1);

-- Order info
-- Fix datestyle to accommodate US date format 'MM-DD-YYYY'
SET datestyle = "ISO, MDY";

INSERT INTO orderinfo(customer_id, date_placed, date_shipped, shipping) VALUES
(3, '03-13-2004', '03-17-2004', 2.99),
(8, '06-23-2004', '06-24-2004', 0.00),
(15, '09-02-2004', '09-12-2004', 3.99),
(13, '09-03-2004', '09-10-2004', 2.99),
(8, '07-21-2004', '07-24-2004', 0.00);

-- Order line
INSERT INTO orderline(orderinfo_id, item_id, quantity) VALUES
(1, 4, 1),
(1, 7, 1),
(1, 9, 1),
(2, 1, 1),
(2, 10, 1),
(2, 7, 2),
(2, 4, 2),
(3, 2, 1),
(3, 1, 1),
(4, 5, 2),
(5, 1, 1),
(5, 3, 1);


