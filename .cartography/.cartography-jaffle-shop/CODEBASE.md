# CODEBASE.md - Living Context Document

Generated: 2026-03-15 05:02:19

This document provides architectural awareness for AI coding agents.

## Architecture Overview

This codebase contains 37 modules organized into 6 semantic domains (9 E-commerce Data Warehousing, 7 Customer Analytics Marts, 5 Data Engineering Tools). The data pipeline processes 19 datasets through 15 transformations. 

## Critical Path

No module import edges detected (SQL/dbt-only repo). Critical path derived from data lineage graph — transformations with the most upstream + downstream connections:

1. **order_items** (connections: 5)
   - Source: `models/marts/order_items.sql`

2. **customers** (connections: 3)
   - Source: `models/marts/customers.sql`

3. **orders** (connections: 3)
   - Source: `models/marts/orders.sql`

4. **products** (connections: 2)
   - Source: `models/marts/products.sql`

5. **locations** (connections: 2)
   - Source: `models/marts/locations.sql`



## Data Sources & Sinks

### Data Sources (6)

- **ecom.raw_customers** - `/home/yosef/Desktop/intensive/jaffle-shop/models/staging/__sources.yml`
- **ecom.raw_items** - `/home/yosef/Desktop/intensive/jaffle-shop/models/staging/__sources.yml`
- **ecom.raw_orders** - `/home/yosef/Desktop/intensive/jaffle-shop/models/staging/__sources.yml`
- **ecom.raw_products** - `/home/yosef/Desktop/intensive/jaffle-shop/models/staging/__sources.yml`
- **ecom.raw_stores** - `/home/yosef/Desktop/intensive/jaffle-shop/models/staging/__sources.yml`
- **ecom.raw_supplies** - `/home/yosef/Desktop/intensive/jaffle-shop/models/staging/__sources.yml`

### Data Sinks (5)

- **customers** - `/home/yosef/Desktop/intensive/jaffle-shop/models/marts/customers.yml`
- **locations** - `models/marts/locations.sql`
- **metricflow_time_spine** - `models/marts/metricflow_time_spine.sql`
- **products** - `models/marts/products.sql`
- **supplies** - `models/marts/supplies.sql`


## Known Debt

### Circular Dependencies (0)

No circular dependencies detected. ✓

### Documentation Drift (0)

No documentation drift detected. ✓


## High-Velocity Files

Files with the most frequent changes (potential pain points):

1. **/home/yosef/Desktop/intensive/jaffle-shop/.pre-commit-config.yaml** (1 commits)
   - This module configures pre-commit hooks for a Python project to automatically enforce code quality standards before commits are finalized. It integrates multiple repositories to check YAML syntax, fix trailing whitespace and end-of-file issues, validate requirements.txt formatting, and use Ruff for Python code formatting and linting with automatic fixes. The configuration ensures consistent code quality and formatting across the development team by running these checks locally before code is pushed to version control.
   - Domain: Data Engineering Tools

2. **/home/yosef/Desktop/intensive/jaffle-shop/packages.yml** (1 commits)



## Module Purpose Index

Complete index of all modules with their purpose statements:

### E-commerce Data Warehousing (9 modules)

- **/home/yosef/Desktop/intensive/jaffle-shop/macros/cents_to_dollars.sql** (sql)
  - This module provides a project-wide macro for converting currency values from cents to dollars across different database platforms. It offers database-specific implementations for PostgreSQL, BigQuery, and Fabric, ensuring consistent numeric formatting with two decimal places. The macro enables uniform financial data transformation throughout the data warehouse, supporting accurate monetary calculations and reporting across heterogeneous database environments.
  - complexity: 22

- **/home/yosef/Desktop/intensive/jaffle-shop/models/marts/products.yml** (yaml)
  - This YAML configuration defines a semantic model for product data in a data mart, establishing a product dimension table with one row per product. The model defines key entities and categorical dimensions including product name, type, description, food/drink classification, and price, enabling structured analysis of product attributes. It serves as a semantic layer that maps the underlying dbt model to business-friendly entities and dimensions for downstream analytics and reporting.
  - complexity: 27

- **/home/yosef/Desktop/intensive/jaffle-shop/models/marts/supplies.yml** (yaml)
  - This YAML configuration defines a semantic model for a supplies dimension table that provides structured access to supply and product combination data. The model establishes a primary entity based on supply UUID and includes categorical dimensions for supply ID, product ID, supply name, supply cost, and perishability status, enabling analytical queries that can slice metrics by these attributes. It serves as a semantic layer that transforms raw supply data into a business-ready format for reporting and analysis within the data warehouse ecosystem.
  - complexity: 25

- **/home/yosef/Desktop/intensive/jaffle-shop/models/staging/__sources.yml** (yaml)
  - This YAML configuration defines a staging layer for e-commerce data sources in the Jaffle Shop data warehouse. It establishes connections to raw tables containing customers, orders, items, stores, products, and supplies data, with specific timestamp fields for tracking data freshness on orders and stores. The module serves as the foundational data ingestion layer, organizing disparate e-commerce data sources into a structured schema for downstream analytics and reporting.
  - complexity: 21

- **/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_locations.sql** (sql)
  - This module transforms raw store data from the e-commerce system into a standardized staging format for the jaffle-shop data warehouse. It extracts key location attributes including IDs, names, tax rates, and opening dates, while standardizing the opened_at timestamp to a date format. The module serves as a foundational data preparation step, converting source system data into a consistent structure for downstream analytics and reporting.
  - complexity: 30

- **/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_order_items.sql** (sql)
  - This module transforms raw e-commerce order item data by renaming key columns to align with the data warehouse schema, specifically converting `id` to `order_item_id`, `order_id` to `order_id`, and `sku` to `product_id`. It serves as a staging layer that prepares raw order item data from the `ecom.raw_items` source for downstream analytics and reporting, ensuring consistent naming conventions across the data pipeline. The module acts as a foundational transformation step in the jaffle-shop data model, enabling reliable analysis of order items, products, and their relationships within the broader e-commerce analytics system.
  - complexity: 23

- **/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_orders.sql** (sql)
  - This module transforms raw e-commerce order data from the source table into a standardized staging format for the jaffle-shop data warehouse. It renames key columns to align with business terminology (e.g., `id` to `order_id`, `store_id` to `location_id`), converts monetary values from cents to dollars for readability, and truncates timestamps to the day level for consistent time-based analysis. The module serves as a foundational data preparation step, ensuring order data is properly structured and formatted for downstream analytics and reporting workflows.
  - complexity: 34

- **/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_products.sql** (sql)
  - This module transforms raw product data from an e-commerce source into a standardized staging format for the jaffle shop. It renames and restructures product attributes, converts prices from cents to dollars, and adds boolean flags to identify food and drink items based on product type. The module serves as a data preparation layer that enables downstream analytics and reporting by providing clean, consistently formatted product information.
  - complexity: 35

- **/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_supplies.sql** (sql)
  - This module transforms raw supply data from the e-commerce system into a standardized staging format for downstream analytics. It generates a unique surrogate key for each supply item, converts cost from cents to dollars, and renames fields to align with the data warehouse schema while preserving key identifiers like supply ID and product SKU. The module serves as an intermediary layer that prepares supply data for consumption by business intelligence tools and reporting systems.
  - complexity: 32

### Customer Analytics Marts (7 modules)

- **/home/yosef/Desktop/intensive/jaffle-shop/models/marts/customers.sql** (sql)
  - This module creates a comprehensive customer mart by joining customer data with their order history to provide a unified view of customer behavior and lifetime value. It calculates key metrics including total orders, first and last purchase dates, total spend (pre-tax, tax, and overall), and classifies customers as either 'new' or 'returning' based on their purchase history. The resulting dataset serves as a foundational mart for customer analytics, enabling business users to analyze customer cohorts, track customer lifetime value, and understand purchasing patterns across the customer base.
  - complexity: 59

- **/home/yosef/Desktop/intensive/jaffle-shop/models/marts/customers.yml** (yaml)
  - This module creates a customer data mart that provides a comprehensive overview of customer information, including order history, spending patterns, and customer classification. It aggregates key metrics such as lifetime spend, order counts, and timestamps to enable analysis of customer behavior and segmentation. The mart serves as a foundational dataset for customer analytics, supporting business intelligence use cases like customer lifetime value analysis, retention tracking, and marketing segmentation.
  - complexity: 108

- **/home/yosef/Desktop/intensive/jaffle-shop/models/marts/order_items.sql** (sql)
  - This module consolidates order item data with related order, product, and supply cost information to provide a comprehensive view of each order item. It joins order items with their corresponding orders, product details, and aggregated supply costs, enabling analysis of order timing, product characteristics, and cost structure. The module serves as a foundational mart for downstream analytics by combining transactional data with product and supply information in a single, queryable dataset.
  - complexity: 67

- **/home/yosef/Desktop/intensive/jaffle-shop/models/marts/order_items.yml** (yaml)
  - This module defines a data mart for order items that validates data integrity through tests ensuring unique order item IDs and proper relationships to orders. It provides a semantic model for analyzing order items at the grain of one row per item, including dimensions for time-based analysis and categorical classifications of food vs drink items. The mart supports business analytics by calculating measures like revenue and supply costs, enabling detailed examination of order composition and profitability.
  - complexity: 182

- **/home/yosef/Desktop/intensive/jaffle-shop/models/marts/orders.sql** (sql)
  - This module creates a comprehensive orders mart that enriches order data with item-level summaries and customer ordering patterns. It calculates key metrics like order cost, item counts, and flags for food/drink orders, then assigns sequential order numbers to each customer's purchases. The resulting dataset serves as a foundation for customer analytics, order tracking, and business intelligence reporting by providing a unified view of orders with detailed item breakdowns and customer-specific ordering context.
  - complexity: 78

- **/home/yosef/Desktop/intensive/jaffle-shop/models/marts/orders.yml** (yaml)
  - This module creates an orders data mart that provides a comprehensive overview of each order, including key details like order totals, timestamps, and whether the order contained food or drink items. It validates data integrity through tests ensuring subtotal calculations are correct and that order IDs are unique and properly linked to customers. The mart serves as a central reference point for order-level analytics, enabling business users to analyze order patterns, customer behavior, and product mix across the jaffle shop's operations.
  - complexity: 184

- **/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_order_items.yml** (yaml)
  - The stg_order_items model captures individual food and drink items that comprise customer orders, with each row representing a single order item. It ensures data integrity through unique identification of order items and maintains referential integrity by validating relationships to the stg_orders table. This staging model serves as a foundational data structure for order processing and analysis, enabling detailed tracking of what specific items were included in each customer order.
  - complexity: 17

### Data Engineering Tools (5 modules)

- **/home/yosef/Desktop/intensive/jaffle-shop/.pre-commit-config.yaml** (yaml)
  - This module configures pre-commit hooks for a Python project to automatically enforce code quality standards before commits are finalized. It integrates multiple repositories to check YAML syntax, fix trailing whitespace and end-of-file issues, validate requirements.txt formatting, and use Ruff for Python code formatting and linting with automatic fixes. The configuration ensures consistent code quality and formatting across the development team by running these checks locally before code is pushed to version control.
  - complexity: 15, changes: 1

- **/home/yosef/Desktop/intensive/jaffle-shop/Taskfile.yml** (yaml)
  - This module manages the lifecycle of a data warehouse environment for a jaffle shop, automating the setup, data generation, and loading processes. It creates a Python virtual environment, installs necessary dependencies including dbt, generates synthetic data for a specified number of years, seeds the database with this data, and provides cleanup functionality. The module serves as a complete orchestration tool for initializing and populating a test data warehouse environment, enabling development and testing of data analytics workflows.
  - complexity: 41

- **/home/yosef/Desktop/intensive/jaffle-shop/dbt_project.yml** (yaml)
  - This is a dbt project configuration file for the jaffle_shop data transformation project. It defines the project structure, model paths, and materialization settings for staging views and mart tables, while also configuring seed data loading and timezone settings for data processing. The configuration establishes the foundation for transforming raw data into analytics-ready models within the dbt framework.
  - complexity: 39

- **/home/yosef/Desktop/intensive/jaffle-shop/macros/generate_schema_name.sql** (sql)
  - This macro generates database schema names based on the execution context and input parameters. It determines the appropriate schema by checking if the resource is a seed, whether a custom schema name is provided, and the target environment (production vs non-production). The macro ensures seeds are placed in a global `raw` schema, applies custom schema names with appropriate prefixes in production, and defaults to the target schema for unspecified cases.
  - complexity: 24

- **/home/yosef/Desktop/intensive/jaffle-shop/models/marts/metricflow_time_spine.sql** (sql)
  - This module generates a time spine containing 10 years of daily dates starting from January 1, 2000, providing a foundational date dimension for time-based analysis. It creates a standardized calendar table that can be used to join with other datasets for temporal analysis, ensuring consistent date handling across the data warehouse. The module serves as a core building block for time-based metrics and reporting by providing a complete date range for filtering and joining operations.
  - complexity: 20

### Data Mart Layer (5 modules)

- **/home/yosef/Desktop/intensive/jaffle-shop/models/marts/locations.sql** (sql)
  - This module serves as a staging layer that extracts and exposes location data from the staging locations table for downstream consumption. It provides a clean, centralized view of location information by selecting all records from the stg_locations source, making this data available for analytical queries and reporting. The module acts as a foundational data mart component that transforms raw staging data into a format suitable for business intelligence and analytics workflows.
  - complexity: 10

- **/home/yosef/Desktop/intensive/jaffle-shop/models/marts/locations.yml** (yaml)
  - This module defines a semantic model for a location dimension table that provides business context for location-based analytics. It enables analysis of location attributes including names and opening dates, while also calculating average tax rates across locations. The model serves as a foundational data mart component that supports time-based analysis of location data through its opened_date grain and categorical attributes.
  - complexity: 25

- **/home/yosef/Desktop/intensive/jaffle-shop/models/marts/products.sql** (sql)
  - This module serves as a mart layer that exposes product data from the staging area for downstream consumption. It retrieves all product records from the stg_products table and makes them available for reporting, analytics, or other business processes that require product information. The module acts as a simple data access point, providing a clean interface to product data without any transformation or business logic.
  - complexity: 10

- **/home/yosef/Desktop/intensive/jaffle-shop/models/marts/supplies.sql** (sql)
  - This module serves as a mart layer that provides a clean, accessible view of supply data for downstream consumption. It retrieves all records from the staging supplies table, acting as a semantic layer that transforms raw supply data into a business-ready format. The module fits into the larger data pipeline by bridging the gap between raw staging data and analytical/reporting needs, ensuring consistent access to supply information across the organization.
  - complexity: 10

- **/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_locations.yml** (yaml)
  - This module transforms raw store data from the ecom system into a cleaned staging table of open locations, applying basic data cleaning and transformation to create one row per location with standardized fields. It ensures data quality by enforcing uniqueness and non-null constraints on the location_id field, and includes unit tests to verify proper timestamp truncation from opened_at to opened_date format. The module serves as a foundational data layer that prepares location information for downstream analytics and reporting by standardizing and validating the raw store data.
  - complexity: 44

### Data Staging Models (5 modules)

- **/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_customers.sql** (sql)
  - This module extracts customer data from the raw e-commerce source table and transforms it by renaming key columns to align with the data warehouse naming conventions. It specifically maps the customer ID and name fields, providing a clean staging layer for customer information that can be used in downstream analytics and reporting. The module serves as a foundational data transformation step in the e-commerce data pipeline, ensuring consistent customer data structure across the organization's analytics ecosystem.
  - complexity: 24

- **/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_customers.yml** (yaml)
  - This module defines a staging model for customer data that applies basic cleaning and transformation to create a single row per customer. It establishes data quality controls by enforcing that customer_id is both not null and unique, ensuring reliable customer identification. The model serves as a foundational data layer that prepares customer information for downstream analytics and business processes.
  - complexity: 10

- **/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_orders.yml** (yaml)
  - This module defines a staging model for order data that applies basic cleaning and transformation to ensure data quality, with one row per order. It includes data validation rules to verify that order totals are calculated correctly (order_total - tax_paid = subtotal) and enforces data integrity by ensuring order_id is both unique and not null. The model serves as a foundational data layer that transforms raw order data into a reliable format for downstream analytics and reporting.
  - complexity: 13

- **/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_products.yml** (yaml)
  - This module defines a staging model for product data that transforms raw product information into a clean, standardized format with one row per product. It establishes product_id as a unique, non-null key field to ensure data integrity and enable reliable joins with other models in the data warehouse. The model serves as a foundational data layer that prepares product information for downstream analytics and reporting workflows.
  - complexity: 10

- **/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_supplies.yml** (yaml)
  - This module defines a staging model for supply expense data that transforms raw supply cost records into a structured format with unique identifiers for each cost entry. It creates a table where each row represents a specific supply cost instance (not aggregated by supply), allowing for tracking of cost fluctuations over time through new UUIDs for each price change. The model enforces data integrity by ensuring each supply cost record has a unique, non-null identifier, supporting downstream analytics on supply expense trends and variations.
  - complexity: 13

### Data Pipeline Automation (4 modules)

- **/home/yosef/Desktop/intensive/jaffle-shop/.github/workflows/cd_prod.yml** (yaml)
  - This GitHub Actions workflow automates the deployment of dbt (data build tool) projects to production environments across three different data warehouses: Snowflake, BigQuery, and PostgreSQL. When code is pushed to the main branch, it triggers parallel jobs that install dependencies, authenticate with dbt Cloud using API credentials, and execute pre-configured dbt Cloud jobs to transform and deploy data models. The workflow serves as a CI/CD pipeline that ensures consistent, automated deployment of data transformations to production data warehouses whenever changes are merged to the main branch.
  - complexity: 80

- **/home/yosef/Desktop/intensive/jaffle-shop/.github/workflows/cd_staging.yml** (yaml)
  - This GitHub Actions workflow automatically deploys dbt Cloud jobs to staging environments across three different data warehouses (Snowflake, BigQuery, and Postgres) whenever code is pushed to the staging branch. It orchestrates the installation of dependencies, sets up the Python environment, and triggers dbt Cloud jobs using API credentials stored in GitHub secrets, enabling continuous integration and deployment of data transformation pipelines. The workflow serves as a bridge between GitHub's version control system and dbt Cloud's data transformation platform, ensuring that changes to data models are automatically tested and deployed to staging environments.
  - complexity: 80

- **/home/yosef/Desktop/intensive/jaffle-shop/.github/workflows/ci.yml** (yaml)
  - This GitHub Actions workflow automatically triggers dbt Cloud jobs for pull requests targeting the main or staging branches, running data transformation tests across three different database platforms (Snowflake, BigQuery, and Postgres). The workflow sets up the environment, installs dependencies, and executes dbt Cloud jobs with branch-specific schema overrides to validate data transformations in isolated environments before merging changes. It serves as a continuous integration pipeline that ensures data model changes are tested across multiple database systems, providing early validation of data transformations in a production-like environment.
  - complexity: 82

- **/home/yosef/Desktop/intensive/jaffle-shop/.github/workflows/scripts/dbt_cloud_run_job.py** (python)
  - This Python module provides programmatic control over dbt (data build tool) jobs through the dbt Cloud API. It enables triggering dbt job executions with configurable parameters like git branch and schema overrides, while also providing functionality to monitor job status through polling mechanisms. The module serves as an automation interface for dbt Cloud operations, allowing external systems to initiate and track data transformation workflows programmatically.
  - complexity: 930

### Uncategorized (2 modules)

- **/home/yosef/Desktop/intensive/jaffle-shop/package-lock.yml** (yaml)
  - _No purpose statement available_
  - complexity: 9

- **/home/yosef/Desktop/intensive/jaffle-shop/packages.yml** (yaml)
  - _No purpose statement available_
  - complexity: 8, changes: 1

