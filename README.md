# Coffee Shop Database

## Overview

This project is a small relational database designed for a multi-tenant coffee shop system. It was built as a practice project to learn database modeling, entity relationships, normalization, and SQL schema design before working on any larger database project.

The goal is not to build a complete point-of-sale system, but to practice designing a realistic relational database from business requirements, populating it with synthetic data and then perform data analysis.

---

## Learning Objectives

- Practice identifying business entities and events.
- Design an Entity-Relationship Diagram (ERD).
- Apply normalization principles.
- Implement a relational schema in PostgreSQL.
- Define primary keys, foreign keys, and constraints.
- Prepare a schema suitable for future SQL analysis.
- generate synethetic data
- perform data analysis

---

## Business Scenario

A coffee shop manages:

- Employees
- Products
- Customer orders
- Order items
- Payments

Each coffee shop operates independently, allowing multiple shops to exist within the same database.

---

## Database Structure

The database consists of the following entities:

- CoffeeShop
- Employee
- Product
- Orders
- OrderItem
- Payment

---

## Features

- Multi-tenant coffee shop model
- Composite primary keys where appropriate
- Referential integrity using foreign keys
- Data validation using CHECK constraints
- Historical order pricing through OrderItem
- Payment tracking

---

## Resources

- PostgreSQL
- SQL

---


## Purpose

This project is part of a self learning journey in relational database design, synthetic data population and data analysis.
The emphasis is on understanding database modeling rather than building a complete production application.
