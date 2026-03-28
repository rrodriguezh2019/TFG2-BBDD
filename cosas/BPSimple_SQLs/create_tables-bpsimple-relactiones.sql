-- Create table customer
CREATE TABLE customer
(
    customer_id                     SERIAL,
    title                           CHAR(4),
    fname                           VARCHAR(32),
    lname                           VARCHAR(32)           NOT NULL,
    addressline                     VARCHAR(64),
    town                            VARCHAR(32),
    zipcode                         CHAR(10)              NOT NULL,
    phone                           VARCHAR(16),
    CONSTRAINT                      customer_pk PRIMARY KEY(customer_id)
);

-- Create table item
CREATE TABLE item
(
    item_id                         SERIAL,
    description                     VARCHAR(64)           NOT NULL,
    cost_price                      NUMERIC(7,2),
    sell_price                      NUMERIC(7,2),
    CONSTRAINT                      item_pk PRIMARY KEY(item_id)
);

-- Create table orderinfo
CREATE TABLE orderinfo
(
    orderinfo_id                    SERIAL,
    customer_id                     INTEGER               NOT NULL,
    date_placed                     DATE                  NOT NULL,
    date_shipped                    DATE,
    shipping                        NUMERIC(7,2),
    CONSTRAINT                      orderinfo_pk PRIMARY KEY(orderinfo_id),
    CONSTRAINT                      fk_customer FOREIGN KEY(customer_id) REFERENCES customer(customer_id) ON DELETE CASCADE
);

-- Create table stock
CREATE TABLE stock
(
    item_id                         INTEGER               NOT NULL,
    quantity                        INTEGER               NOT NULL,
    CONSTRAINT                      stock_pk PRIMARY KEY(item_id),
    CONSTRAINT                      fk_item FOREIGN KEY(item_id) REFERENCES item(item_id) ON DELETE CASCADE
);


-- Create table orderline
CREATE TABLE orderline
(
    orderinfo_id                    INTEGER               NOT NULL,
    item_id                         INTEGER               NOT NULL,
    quantity                        INTEGER               NOT NULL,
    CONSTRAINT                      orderline_pk PRIMARY KEY(orderinfo_id, item_id),
    CONSTRAINT                      fk_orderinfo FOREIGN KEY(orderinfo_id) REFERENCES orderinfo(orderinfo_id) ON DELETE CASCADE,
    CONSTRAINT                      fk_orderline_item FOREIGN KEY(item_id) REFERENCES item(item_id) ON DELETE CASCADE
);

-- Create table barcode
CREATE TABLE barcode
(
    barcode_ean                     CHAR(13)              NOT NULL,
    item_id                         INTEGER               NOT NULL,
    CONSTRAINT                      barcode_pk PRIMARY KEY(barcode_ean),
    CONSTRAINT                      fk_barcode_item FOREIGN KEY(item_id) REFERENCES item(item_id) ON DELETE CASCADE
);
