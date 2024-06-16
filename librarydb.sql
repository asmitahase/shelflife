CREATE DATABASE IF NOT EXISTS `library`;
USE `library`;
CREATE TABLE IF NOT EXISTS `books` (
    `book_id` INT NOT NULL AUTO_INCREMENT,
    `title` VARCHAR(256) NOT NULL,
    `authors` VARCHAR(256) NOT NULL,
    `isbn` VARCHAR(10) NOT NULL UNIQUE,
    `isbn13` VARCHAR(13) NOT NULL UNIQUE,
    `language_code` VARCHAR(3) NOT NULL,
    `num_of_pages` INT NOT NULL,
    `publisher` VARCHAR(256) NOT NULL,
    `publication_date` DATE NOT NULL,
    `total_count` INT NOT NULL,
    `rented_count` INT NOT NULL DEFAULT 0,
    `available_count` INT NOT NULL,
    `ratings_count` INT NULL,
    `text_reviews_count` INT NULL,
    `average_rating` FLOAT NULL,
    `created_date` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `modified_date` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `renting_cost` INT NOT NULL DEFAULT 0,
    PRIMARY KEY (`book_id`)
);
CREATE TABLE IF NOT EXISTS `members` (
    `member_id` INT NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(256) NOT NULL,
    `email` VARCHAR(256) NOT NULL UNIQUE,
    `created_date` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `modified_date` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `outstanding_debt` FLOAT NOT NULL DEFAULT 0,
    PRIMARY KEY (`member_id`)
);
CREATE TABLE IF NOT EXISTS `transactions` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `book_id` INT NOT NULL,
    `member_id` INT NOT NULL,
    `issued_on` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `returned_on` TIMESTAMP NULL,
    `amount_paid` FLOAT NULL,
    PRIMARY KEY (`id`),
    FOREIGN KEY (`book_id`) REFERENCES books(`book_id`),
    FOREIGN KEY (`member_id`) REFERENCES members(`member_id`)
);
