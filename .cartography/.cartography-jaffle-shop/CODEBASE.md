# CODEBASE.md - Living Context Document

Generated: 2026-03-14 08:15:44

This document provides architectural awareness for AI coding agents.

## Architecture Overview

This codebase contains 37 modules organized into 6 semantic domains (14 Data Warehousing, 7 Data Warehouse Management, 7 Customer Analytics). The data pipeline processes 19 datasets through 15 transformations. 

## Critical Path

The following modules are architectural hubs (highest PageRank scores):

1. **/home/yosef/Desktop/intensive/jaffle-shop/.pre-commit-config.yaml** (PageRank: 0.0270)
   - This module configures pre-commit hooks for a Python project to automatically enforce code quality standards before commits are finalized. It integrates multiple repositories to check YAML syntax, fix trailing whitespace and end-of-file issues, validate requirements.txt formatting, and use Ruff for Python code formatting and linting with automatic fixes. The configuration ensures consistent code quality and formatting across the development team by running these checks locally before code is pushed to version control.
   - Domain: Code Quality Assurance

2. **/home/yosef/Desktop/intensive/jaffle-shop/package-lock.yml** (PageRank: 0.0270)

3. **/home/yosef/Desktop/intensive/jaffle-shop/Taskfile.yml** (PageRank: 0.0270)
   - This module manages the lifecycle of a data warehouse environment for a jaffle shop, automating the setup, data generation, and loading processes. It creates a Python virtual environment, installs necessary dependencies including dbt and database-specific adapters, generates synthetic data for a configurable number of years, and seeds the data warehouse with this information. The module provides a complete workflow from environment setup through data loading and cleanup, enabling reproducible data warehouse initialization for testing or development purposes.
   - Domain: Data Warehouse Management

4. **/home/yosef/Desktop/intensive/jaffle-shop/packages.yml** (PageRank: 0.0270)

5. **/home/yosef/Desktop/intensive/jaffle-shop/dbt_project.yml** (PageRank: 0.0270)
   - This is a dbt project configuration file for the jaffle_shop data transformation project. It defines the project structure, model paths, and materialization settings for staging views and mart tables, while also configuring seed data loading and timezone settings for data processing. The configuration establishes the foundation for transforming raw data into analytics-ready models within the dbt framework.
   - Domain: Data Warehouse Management



## Data Sources & Sinks

### Data Sources (6)

- **ecom.raw_customers** (table) - discovered in `inferred_from_transformations`
- **ecom.raw_items** (table) - discovered in `inferred_from_transformations`
- **ecom.raw_orders** (table) - discovered in `inferred_from_transformations`
- **ecom.raw_products** (table) - discovered in `inferred_from_transformations`
- **ecom.raw_stores** (table) - discovered in `inferred_from_transformations`
- **ecom.raw_supplies** (table) - discovered in `inferred_from_transformations`

### Data Sinks (5)

- **customers** (table) - discovered in `models/marts/customers.sql`
- **locations** (table) - discovered in `models/marts/locations.sql`
- **metricflow_time_spine** (table) - discovered in `models/marts/metricflow_time_spine.sql`
- **products** (table) - discovered in `models/marts/products.sql`
- **supplies** (table) - discovered in `models/marts/supplies.sql`


## Known Debt

### Circular Dependencies (0)

No circular dependencies detected. ✓

### Documentation Drift (0)

No documentation drift detected. ✓


## High-Velocity Files

Files with the most frequent changes (potential pain points):

1. **/home/yosef/Desktop/intensive/jaffle-shop/.pre-commit-config.yaml** (1 commits)
   - This module configures pre-commit hooks for a Python project to automatically enforce code quality standards before commits are finalized. It integrates multiple repositories to check YAML syntax, fix trailing whitespace and end-of-file issues, validate requirements.txt formatting, and use Ruff for Python code formatting and linting with automatic fixes. The configuration ensures consistent code quality and formatting across the development team by running these checks locally before code is pushed to version control.
   - Domain: Code Quality Assurance

2. **/home/yosef/Desktop/intensive/jaffle-shop/packages.yml** (1 commits)



## Module Purpose Index

Complete index of all modules with their purpose statements:

### Data Warehousing (14 modules)

- **/home/yosef/Desktop/intensive/jaffle-shop/macros/generate_schema_name.sql** (sql)
  - This macro generates database schema names based on the execution context and node type. It routes seed data to a global `raw` schema, uses the default target schema for unspecified schemas, and prepends the default schema to custom schema names in production environments while using the default schema for non-production targets. The macro provides a flexible schema naming strategy that adapts to different deployment environments and data types.
  - complexity: 24

- **/home/yosef/Desktop/intensive/jaffle-shop/models/marts/locations.sql** (sql)
  - This module creates a mart view for location data by selecting all records from the staging locations table. It serves as a simple data transformation layer that makes location information available for downstream analytics and reporting. The module acts as an intermediary between raw staging data and analytical models, providing a clean, queryable interface for location-based business intelligence.
  - complexity: 10

- **/home/yosef/Desktop/intensive/jaffle-shop/models/marts/products.sql** (sql)
  - This module serves as a mart layer that exposes product data from the staging environment to downstream consumers. It retrieves all product records from the stg_products table, providing a clean interface for analytics and reporting on product information. The module acts as a simple data access point, enabling business users to query current product data without needing to understand the underlying staging structure.
  - complexity: 10

- **/home/yosef/Desktop/intensive/jaffle-shop/models/marts/supplies.sql** (sql)
  - This module serves as a mart layer that provides a clean, accessible view of supply data for downstream consumption. It retrieves all records from the staging supplies table, acting as a semantic layer that transforms raw supply data into a format suitable for analytics and reporting. The module fits into the larger data pipeline by bridging the staging layer with consumption layers, ensuring consistent access to supply information across the organization.
  - complexity: 10

- **/home/yosef/Desktop/intensive/jaffle-shop/models/marts/supplies.yml** (yaml)
  - This YAML configuration defines a semantic model for a supplies dimension table that provides structured access to supply and product combination data. The model establishes a primary entity based on supply UUID and includes categorical dimensions for supply ID, product ID, supply name, supply cost, and perishability status, enabling analytical queries that can slice metrics by these attributes. It serves as a semantic layer that transforms raw supply data into a business-ready format for reporting and analysis within the data warehouse ecosystem.
  - complexity: 25

- **/home/yosef/Desktop/intensive/jaffle-shop/models/staging/__sources.yml** (yaml)
  - This YAML module defines the source configuration for staging layer data in a data warehouse, specifically for e-commerce data from the Jaffle Shop. It establishes connections to raw tables containing customers, orders, items, stores, products, and supplies data, with metadata about when certain tables were loaded. The module serves as the foundation for data ingestion, providing a structured way to reference and access raw e-commerce data that will be transformed and modeled in subsequent layers of the data pipeline.
  - complexity: 21

- **/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_customers.sql** (sql)
  - This module extracts customer data from the raw e-commerce source table and transforms it by renaming key columns to align with the data warehouse schema. It specifically maps the customer ID and name fields, providing a clean staging layer for downstream analytics and reporting. The module serves as a foundational data preparation step in the e-commerce data pipeline, ensuring consistent customer data formatting for business intelligence use cases.
  - complexity: 24

- **/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_customers.yml** (yaml)
  - This module defines a staging model for customer data that applies basic cleaning and transformation to ensure data quality. It enforces data integrity by validating that each customer has a unique, non-null identifier, providing a reliable foundation for downstream analytics. The model serves as a standardized source of customer information, transforming raw data into a consistent format with one row per customer for use in the broader data warehouse.
  - complexity: 10

- **/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_order_items.sql** (sql)
  - This module extracts raw order item data from the ecom.raw_items source and transforms it by renaming key columns to align with the data warehouse schema. It maps the original id to order_item_id, preserves the order_id relationship, and converts sku to product_id for downstream analytics. The module serves as a staging layer that standardizes order item data for consumption by business intelligence and reporting systems.
  - complexity: 23

- **/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_orders.sql** (sql)
  - This module transforms raw e-commerce order data from the source table into a standardized staging format for the jaffle-shop data warehouse. It renames key columns to align with business terminology (e.g., `id` to `order_id`, `store_id` to `location_id`), converts monetary values from cents to dollars for readability, and truncates timestamps to the day level for consistent time-based analysis. The module serves as a foundational data preparation step, ensuring order data is properly structured and formatted for downstream analytics and reporting workflows.
  - complexity: 34

- **/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_orders.yml** (yaml)
  - This module defines a staging model for order data that applies basic cleaning and transformation to create a single row per order. It includes data quality validations to ensure order totals are mathematically consistent and that order IDs are unique and non-null. The model serves as a foundational data layer for downstream analytics and reporting by providing cleaned, validated order information.
  - complexity: 13

- **/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_products.sql** (sql)
  - This module transforms raw product data from an e-commerce source into a standardized staging format for the jaffle shop. It renames and restructures product attributes, converts prices from cents to dollars, and adds boolean flags to identify food and drink items based on product type. The module serves as a data preparation layer that enables downstream analytics and reporting by providing consistent, enriched product information.
  - complexity: 35

- **/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_supplies.sql** (sql)
  - This module transforms raw supply data from the ecom system into a standardized staging format for the jaffle-shop data warehouse. It generates a unique supply identifier, converts cost from cents to dollars, and standardizes column names while preserving key attributes like product ID, supply name, and perishability status. The module serves as an intermediary layer that prepares supply data for downstream analytics and reporting by creating a consistent, business-ready data structure.
  - complexity: 32

- **/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_supplies.yml** (yaml)
  - This module defines a staging model for supply expense data that transforms raw supply cost records into a structured format with unique identifiers for each cost variation. It creates a table where each row represents a specific supply cost instance (not aggregated by supply), allowing tracking of cost fluctuations over time through new UUIDs for each price change. The model enforces data integrity by ensuring each supply cost record has a unique, non-null identifier, supporting downstream analytics on supply expense trends and variations.
  - complexity: 13

### Data Warehouse Management (7 modules)

- **/home/yosef/Desktop/intensive/jaffle-shop/Taskfile.yml** (yaml)
  - This module manages the lifecycle of a data warehouse environment for a jaffle shop, automating the setup, data generation, and loading processes. It creates a Python virtual environment, installs necessary dependencies including dbt and database-specific adapters, generates synthetic data for a configurable number of years, and seeds the data warehouse with this information. The module provides a complete workflow from environment setup through data loading and cleanup, enabling reproducible data warehouse initialization for testing or development purposes.
  - complexity: 41

- **/home/yosef/Desktop/intensive/jaffle-shop/dbt_project.yml** (yaml)
  - This is a dbt project configuration file for the jaffle_shop data transformation project. It defines the project structure, model paths, and materialization settings for staging views and mart tables, while also configuring seed data loading and timezone settings for data processing. The configuration establishes the foundation for transforming raw data into analytics-ready models within the dbt framework.
  - complexity: 39

- **/home/yosef/Desktop/intensive/jaffle-shop/macros/cents_to_dollars.sql** (sql)
  - This module provides a database-agnostic macro for converting currency values stored as cents to their equivalent dollar amounts with two decimal places. It supports multiple database platforms (default, PostgreSQL, BigQuery, and Fabric) by implementing platform-specific SQL syntax for the conversion operation. The macro enables consistent currency formatting across different data warehouse environments, ensuring financial data is properly scaled and displayed in standard dollar notation.
  - complexity: 22

- **/home/yosef/Desktop/intensive/jaffle-shop/models/marts/locations.yml** (yaml)
  - This module defines a semantic model for a location dimension table that provides business context for location-based analytics. It enables analysis of location attributes including names and opening dates, along with calculating average tax rates across locations. The model serves as a foundational data mart component that supports location-centric reporting and analysis within the jaffle-shop's data warehouse.
  - complexity: 25

- **/home/yosef/Desktop/intensive/jaffle-shop/models/marts/metricflow_time_spine.sql** (sql)
  - This module generates a time spine containing 10 years of daily dates starting from January 1, 2000, providing a foundational date dimension for time-based analysis. It creates a standardized calendar table that can be used to join with other datasets for temporal analysis, ensuring consistent date handling across the data warehouse. The module serves as a core building block for time-based reporting and analytics by providing a complete date range for filtering and joining operations.
  - complexity: 20

- **/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_locations.sql** (sql)
  - This module transforms raw store data from the e-commerce system into a standardized staging format for the jaffle-shop data warehouse. It extracts key location attributes including IDs, names, tax rates, and opening dates, while standardizing the opened_at timestamp to a daily grain. The module serves as a foundational data preparation step, converting source system data into a consistent format suitable for downstream analytics and reporting.
  - complexity: 30

- **/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_locations.yml** (yaml)
  - This module transforms raw store data from the ecom system into a cleaned staging table of open locations, truncating timestamp fields to dates and ensuring data quality through null and uniqueness constraints on location IDs. It provides a standardized view of location information including names, tax rates, and opening dates that can be used by downstream analytics models. The transformation includes basic data cleaning and validation to ensure reliable location data for business reporting and analysis.
  - complexity: 44

### Customer Analytics (7 modules)

- **/home/yosef/Desktop/intensive/jaffle-shop/models/marts/customers.sql** (sql)
  - This module creates a comprehensive customer mart by joining customer data with their order history to provide a unified view of customer behavior and lifetime value. It calculates key metrics including total orders, first and last purchase dates, total spend (pre-tax, tax, and overall), and categorizes customers as either 'new' or 'returning' based on their purchase history. The mart serves as a foundational dataset for customer analytics, enabling business users to understand customer lifetime value, purchase patterns, and segment customers for targeted marketing or retention strategies.
  - complexity: 59

- **/home/yosef/Desktop/intensive/jaffle-shop/models/marts/customers.yml** (yaml)
  - This module creates a customer data mart that provides a comprehensive overview of customer information, including order history, spending patterns, and customer classification. It aggregates key metrics such as lifetime spend, order counts, and timestamps to enable analysis of customer behavior and segmentation. The mart serves as a foundational dataset for customer analytics, supporting business intelligence use cases like customer lifetime value analysis, retention tracking, and targeted marketing campaigns.
  - complexity: 108

- **/home/yosef/Desktop/intensive/jaffle-shop/models/marts/order_items.sql** (sql)
  - This module consolidates order item data with related order, product, and supply information to provide a comprehensive view of each order item. It joins order items with their corresponding orders, product details, and aggregated supply costs, enabling analysis of order timing, product characteristics, and cost components. The module serves as a foundational mart for downstream analytics by combining transactional data with product and supply information in a single, queryable dataset.
  - complexity: 67

- **/home/yosef/Desktop/intensive/jaffle-shop/models/marts/order_items.yml** (yaml)
  - The order_items module creates and validates a mart table that contains detailed information about individual items within customer orders, including their costs and relationships to products and orders. It provides data quality tests to ensure unique order item IDs and proper foreign key relationships, while also defining semantic models for business analysis including revenue calculations and categorization of items as food or drink. This module serves as a foundational data layer that enables downstream analytics and reporting on order composition, profitability, and product performance across the jaffle-shop's operations.
  - complexity: 182

- **/home/yosef/Desktop/intensive/jaffle-shop/models/marts/orders.sql** (sql)
  - This module creates a comprehensive orders mart that enriches order data with item-level summaries and customer ordering patterns. It calculates key metrics like order cost, item counts, and flags for food/drink orders, then assigns sequential order numbers to each customer's purchases. The mart serves as a foundational dataset for analyzing customer behavior, order composition, and purchasing trends across the jaffle shop's operations.
  - complexity: 78

- **/home/yosef/Desktop/intensive/jaffle-shop/models/marts/orders.yml** (yaml)
  - The orders mart provides a consolidated view of order data, including key details like order totals, timestamps, and cost breakdowns. It offers business-critical insights through calculated fields that identify whether orders contain food or drink items, and validates data integrity through comprehensive tests ensuring subtotal and total calculations are accurate. This mart serves as a foundational data layer for downstream analytics and reporting, enabling analysis of order patterns, customer behavior, and operational costs across the jaffle shop's business operations.
  - complexity: 184

- **/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_order_items.yml** (yaml)
  - The stg_order_items model captures individual food and drink items that comprise customer orders, with each row representing a single order item. It ensures data integrity through unique identification of order items and maintains referential integrity by validating relationships to the stg_orders table. This staging model serves as a foundational data structure for order processing and analysis, enabling detailed tracking of what specific items were included in each customer order.
  - complexity: 17

### Data Pipeline Automation (4 modules)

- **/home/yosef/Desktop/intensive/jaffle-shop/.github/workflows/cd_prod.yml** (yaml)
  - This GitHub Actions workflow automates the deployment of dbt (data build tool) projects to production environments across three different data warehouses: Snowflake, BigQuery, and PostgreSQL. When code is pushed to the main branch, it triggers parallel jobs that install dependencies, authenticate with dbt Cloud using API credentials, and execute pre-configured dbt Cloud jobs to transform and deploy data models. The workflow serves as a CI/CD pipeline that ensures consistent, automated deployment of data transformations to production data warehouses whenever changes are merged to the main branch.
  - complexity: 80

- **/home/yosef/Desktop/intensive/jaffle-shop/.github/workflows/cd_staging.yml** (yaml)
  - This GitHub Actions workflow automatically deploys dbt Cloud jobs to staging environments across three different data warehouses (Snowflake, BigQuery, and Postgres) whenever code is pushed to the staging branch. It orchestrates the execution of specific dbt Cloud jobs by setting up the environment, installing dependencies, and triggering the deployment through a Python script. The workflow serves as a CI/CD pipeline that ensures consistent data transformation deployments across multiple database platforms whenever staging code changes are committed.
  - complexity: 80

- **/home/yosef/Desktop/intensive/jaffle-shop/.github/workflows/ci.yml** (yaml)
  - This GitHub Actions workflow automatically triggers dbt Cloud jobs for pull requests targeting the main or staging branches, running data transformation tests across multiple database platforms (Snowflake, BigQuery, and Postgres). It sets up the environment with specific dbt Cloud job configurations, installs dependencies using uv, and executes the dbt Cloud job script to validate data transformations in isolated schemas based on the pull request branch name. The workflow serves as a continuous integration mechanism to ensure data model changes are tested across different database systems before merging, helping maintain data quality and consistency in the jaffle-shop project.
  - complexity: 82

- **/home/yosef/Desktop/intensive/jaffle-shop/.github/workflows/scripts/dbt_cloud_run_job.py** (python)
  - This Python module provides programmatic control over dbt (data build tool) jobs through the dbt Cloud API. It enables triggering dbt job runs with configurable parameters like git branch and schema overrides, while monitoring job status through a mapping of integer codes to human-readable states. The module serves as an automation interface for dbt Cloud operations, allowing external systems to initiate and track data transformation workflows programmatically.
  - complexity: 930

### Uncategorized (2 modules)

- **/home/yosef/Desktop/intensive/jaffle-shop/package-lock.yml** (yaml)
  - _No purpose statement available_
  - complexity: 9

- **/home/yosef/Desktop/intensive/jaffle-shop/packages.yml** (yaml)
  - _No purpose statement available_
  - complexity: 8, changes: 1

### Product Analytics (2 modules)

- **/home/yosef/Desktop/intensive/jaffle-shop/models/marts/products.yml** (yaml)
  - This semantic model defines a product dimension table that provides structured product data for analytics, with each row representing a unique product identified by product_id. The model includes categorical dimensions for product attributes like name, type, description, and pricing flags, enabling analysis of products by various characteristics. It serves as a foundational data mart component that allows business users to query and analyze product-related metrics across different product categories and attributes.
  - complexity: 27

- **/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_products.yml** (yaml)
  - This module defines a staging model for product data that transforms raw product information into a clean, standardized format with one row per product. It establishes product_id as a unique, non-null key field to ensure data integrity and enable reliable joins with other models in the data warehouse. The model serves as a foundational data layer that prepares product information for downstream analytics and reporting workflows.
  - complexity: 10

### Code Quality Assurance (1 modules)

- **/home/yosef/Desktop/intensive/jaffle-shop/.pre-commit-config.yaml** (yaml)
  - This module configures pre-commit hooks for a Python project to automatically enforce code quality standards before commits are finalized. It integrates multiple repositories to check YAML syntax, fix trailing whitespace and end-of-file issues, validate requirements.txt formatting, and use Ruff for Python code formatting and linting with automatic fixes. The configuration ensures consistent code quality and formatting across the development team by running these checks locally before code is pushed to version control.
  - complexity: 15, changes: 1

