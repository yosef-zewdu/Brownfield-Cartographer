# Onboarding Brief - Day-One Questions

This document answers the Five FDE Day-One Questions to help new developers 
quickly understand the codebase architecture and critical components.

## Analysis Metadata

- **Generated:** 2026-03-14T08:15:44.712481
- **Modules Analyzed:** 0
- **Datasets Identified:** 0
- **Transformations Tracked:** 0


## Question 1: Where does data come from?

### Answer

Data comes from six raw tables in the ecom schema, which are ingested through dbt model transformations in the staging layer.

The raw data sources are:
- `ecom.raw_items` (inferred from transformations)
- `ecom.raw_stores` (inferred from transformations) 
- `ecom.raw_supplies` (inferred from transformations)
- `ecom.raw_products` (inferred from transformations)
- `ecom.raw_orders` (inferred from transformations)
- `ecom.raw_customers` (inferred from transformations)

These are transformed into staging models in `models/staging/`:
- `stg_orders.sql:1-34` transforms `ecom.raw_orders`
- `stg_products.sql:1-35` transforms `ecom.raw_products` 
- `stg_supplies.sql:1-32` transforms `ecom.raw_supplies`
- `stg_order_items.sql:1-23` transforms `ecom.raw_items`
- `stg_customers.sql:1-24` transforms `ecom.raw_customers`
- `stg_locations.sql:1-30` transforms `ecom.raw_stores`

The staging models serve as the foundation for downstream analytics and business logic.

### Evidence

1. **Data Source:** `ecom.raw_items` (table)
   - Location: `inferred_from_transformations`
   - Confidence: 0.50

2. **Data Source:** `ecom.raw_stores` (table)
   - Location: `inferred_from_transformations`
   - Confidence: 0.50

3. **Data Source:** `ecom.raw_supplies` (table)
   - Location: `inferred_from_transformations`
   - Confidence: 0.50

4. **Data Source:** `ecom.raw_products` (table)
   - Location: `inferred_from_transformations`
   - Confidence: 0.50

5. **Data Source:** `ecom.raw_orders` (table)
   - Location: `inferred_from_transformations`
   - Confidence: 0.50

6. **Data Source:** `ecom.raw_customers` (table)
   - Location: `inferred_from_transformations`
   - Confidence: 0.50

7. **Ingestion:** dbt_model transformation
   - Location: `models/staging/stg_orders.sql`:1-34
   - Sources: ecom.raw_orders
   - Confidence: 1.00

8. **Ingestion:** dbt_model transformation
   - Location: `models/staging/stg_products.sql`:1-35
   - Sources: ecom.raw_products
   - Confidence: 1.00

9. **Ingestion:** dbt_model transformation
   - Location: `models/staging/stg_supplies.sql`:1-32
   - Sources: ecom.raw_supplies
   - Confidence: 1.00

10. **Ingestion:** dbt_model transformation
   - Location: `models/staging/stg_order_items.sql`:1-23
   - Sources: ecom.raw_items
   - Confidence: 1.00

11. **Ingestion:** dbt_model transformation
   - Location: `models/staging/stg_customers.sql`:1-24
   - Sources: ecom.raw_customers
   - Confidence: 1.00

12. **Ingestion:** dbt_model transformation
   - Location: `models/staging/stg_locations.sql`:1-30
   - Sources: ecom.raw_stores
   - Confidence: 1.00

### Confidence

- **Evidence Type:** heuristic
- **Confidence Score:** 0.80
- **Resolution Status:** resolved


## Question 2: What are the critical outputs?

### Answer

The critical outputs are five tables in the marts directory:

1. `customers` table - `models/marts/customers.sql:1-59`
2. `products` table - `models/marts/products.sql:1-10`  
3. `metricflow_time_spine` table - `models/marts/metricflow_time_spine.sql:1-20`
4. `locations` table - `models/marts/locations.sql:1-10`
5. `supplies` table - `models/marts/supplies.sql:1-10`

These are the main tables that downstream processes (num_sinks: 5) depend on. New developers should prioritize understanding these five tables as they represent the core outputs of the data transformation pipeline.

### Evidence

1. **Critical Output:** `customers` (table)
   - Location: `models/marts/customers.sql`:1-59
   - Confidence: 1.00

2. **Critical Output:** `products` (table)
   - Location: `models/marts/products.sql`:1-10
   - Confidence: 1.00

3. **Critical Output:** `metricflow_time_spine` (table)
   - Location: `models/marts/metricflow_time_spine.sql`:1-20
   - Confidence: 1.00

4. **Critical Output:** `locations` (table)
   - Location: `models/marts/locations.sql`:1-10
   - Confidence: 1.00

5. **Critical Output:** `supplies` (table)
   - Location: `models/marts/supplies.sql`:1-10
   - Confidence: 1.00

### Confidence

- **Evidence Type:** heuristic
- **Confidence Score:** 0.85
- **Resolution Status:** resolved


## Question 3: What happens if critical components break?

### Answer

If critical components break, the impact can be severe and widespread across the codebase. Based on the blast radius analysis:

**ecom.raw_items** (`Evidence 1`) affects 8 components including `dbt_model:stg_order_items`, `stg_order_items`, `customers`, and `order_items`. This suggests that breaking this component would disrupt order processing and customer data flows.

**ecom.raw_stores** (`Evidence 2`) impacts 4 components including `locations` and `stg_locations`. A failure here would affect store location data and related operations.

**ecom.raw_supplies** (`Evidence 3`) has the largest blast radius, affecting 10 components including `supplies`, `dbt_model:stg_supplies`, `customers`, and `order_items`. This indicates that breaking this component would have cascading effects on both supply chain operations and customer/order management systems.

The most critical finding is that **ecom.raw_supplies** affects the most components (10), making it the highest priority for stability and monitoring. New developers should be particularly cautious when modifying this component due to its extensive dependencies.

### Evidence

1. **Blast Radius:** `ecom.raw_items`
   - Affected Components: 8
   - Examples: dbt_model:stg_order_items, stg_order_items, customers, order_items, dbt_model:customers
   - Location: `ecom.raw_items`

2. **Blast Radius:** `ecom.raw_stores`
   - Affected Components: 4
   - Examples: locations, stg_locations, dbt_model:stg_locations, dbt_model:locations
   - Location: `ecom.raw_stores`

3. **Blast Radius:** `ecom.raw_supplies`
   - Affected Components: 10
   - Examples: supplies, dbt_model:stg_supplies, customers, order_items, stg_supplies
   - Location: `ecom.raw_supplies`

### Confidence

- **Evidence Type:** heuristic
- **Confidence Score:** 0.90
- **Resolution Status:** resolved


## Question 4: Where does business logic live?

### Answer

Based on the evidence, business logic in this codebase lives primarily in the dbt models within the `models/` directory, particularly in the staging and mart layers.

The business logic is implemented through SQL transformations that:
- Convert data formats (e.g., `/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_products.sql:1-20` converts prices from cents to dollars)
- Restructure data to align with business terminology (e.g., `/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_orders.sql:1-15` renames columns like `id` to `order_id`)
- Add business-specific flags and categorizations (e.g., `/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_products.sql:21-30` adds boolean flags for food/drink items)
- Calculate business metrics (e.g., `/home/yosef/Desktop/intensive/jaffle-shop/models/marts/orders.yml:1-25` calculates order totals and identifies food/drink items)

The business logic is organized in a layered architecture:
1. Staging models transform raw data into business-ready formats
2. Mart models aggregate and calculate business metrics
3. YAML files define data quality tests and semantic models

This separation ensures business logic is centralized in the data transformation layer rather than scattered throughout the codebase.

### Evidence

1. **Domain:** Code Quality Assurance
   - Module Count: 1
   - Representative Modules:
     - `/home/yosef/Desktop/intensive/jaffle-shop/.pre-commit-config.yaml`: This module configures pre-commit hooks for a Python project to automatically enforce code quality standards before commits are finalized. It integrates multiple repositories to check YAML syntax, fix trailing whitespace and end-of-file issues, validate requirements.txt formatting, and use Ruff for Python code formatting and linting with automatic fixes. The configuration ensures consistent code quality and formatting across the development team by running these checks locally before code is pushed to version control.

2. **Domain:** Data Warehouse Management
   - Module Count: 7
   - Representative Modules:
     - `/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_locations.yml`: This module transforms raw store data from the ecom system into a cleaned staging table of open locations, truncating timestamp fields to dates and ensuring data quality through null and uniqueness constraints on location IDs. It provides a standardized view of location information including names, tax rates, and opening dates that can be used by downstream analytics models. The transformation includes basic data cleaning and validation to ensure reliable location data for business reporting and analysis.
     - `/home/yosef/Desktop/intensive/jaffle-shop/Taskfile.yml`: This module manages the lifecycle of a data warehouse environment for a jaffle shop, automating the setup, data generation, and loading processes. It creates a Python virtual environment, installs necessary dependencies including dbt and database-specific adapters, generates synthetic data for a configurable number of years, and seeds the data warehouse with this information. The module provides a complete workflow from environment setup through data loading and cleanup, enabling reproducible data warehouse initialization for testing or development purposes.
     - `/home/yosef/Desktop/intensive/jaffle-shop/dbt_project.yml`: This is a dbt project configuration file for the jaffle_shop data transformation project. It defines the project structure, model paths, and materialization settings for staging views and mart tables, while also configuring seed data loading and timezone settings for data processing. The configuration establishes the foundation for transforming raw data into analytics-ready models within the dbt framework.

3. **Domain:** Data Warehousing
   - Module Count: 14
   - Representative Modules:
     - `/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_products.sql`: This module transforms raw product data from an e-commerce source into a standardized staging format for the jaffle shop. It renames and restructures product attributes, converts prices from cents to dollars, and adds boolean flags to identify food and drink items based on product type. The module serves as a data preparation layer that enables downstream analytics and reporting by providing consistent, enriched product information.
     - `/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_orders.sql`: This module transforms raw e-commerce order data from the source table into a standardized staging format for the jaffle-shop data warehouse. It renames key columns to align with business terminology (e.g., `id` to `order_id`, `store_id` to `location_id`), converts monetary values from cents to dollars for readability, and truncates timestamps to the day level for consistent time-based analysis. The module serves as a foundational data preparation step, ensuring order data is properly structured and formatted for downstream analytics and reporting workflows.
     - `/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_supplies.sql`: This module transforms raw supply data from the ecom system into a standardized staging format for the jaffle-shop data warehouse. It generates a unique supply identifier, converts cost from cents to dollars, and standardizes column names while preserving key attributes like product ID, supply name, and perishability status. The module serves as an intermediary layer that prepares supply data for downstream analytics and reporting by creating a consistent, business-ready data structure.

4. **Domain:** Customer Analytics
   - Module Count: 7
   - Representative Modules:
     - `/home/yosef/Desktop/intensive/jaffle-shop/models/marts/orders.yml`: The orders mart provides a consolidated view of order data, including key details like order totals, timestamps, and cost breakdowns. It offers business-critical insights through calculated fields that identify whether orders contain food or drink items, and validates data integrity through comprehensive tests ensuring subtotal and total calculations are accurate. This mart serves as a foundational data layer for downstream analytics and reporting, enabling analysis of order patterns, customer behavior, and operational costs across the jaffle shop's business operations.
     - `/home/yosef/Desktop/intensive/jaffle-shop/models/marts/order_items.yml`: The order_items module creates and validates a mart table that contains detailed information about individual items within customer orders, including their costs and relationships to products and orders. It provides data quality tests to ensure unique order item IDs and proper foreign key relationships, while also defining semantic models for business analysis including revenue calculations and categorization of items as food or drink. This module serves as a foundational data layer that enables downstream analytics and reporting on order composition, profitability, and product performance across the jaffle-shop's operations.
     - `/home/yosef/Desktop/intensive/jaffle-shop/models/marts/customers.yml`: This module creates a customer data mart that provides a comprehensive overview of customer information, including order history, spending patterns, and customer classification. It aggregates key metrics such as lifetime spend, order counts, and timestamps to enable analysis of customer behavior and segmentation. The mart serves as a foundational dataset for customer analytics, supporting business intelligence use cases like customer lifetime value analysis, retention tracking, and targeted marketing campaigns.

5. **Domain:** Product Analytics
   - Module Count: 2
   - Representative Modules:
     - `/home/yosef/Desktop/intensive/jaffle-shop/models/marts/products.yml`: This semantic model defines a product dimension table that provides structured product data for analytics, with each row representing a unique product identified by product_id. The model includes categorical dimensions for product attributes like name, type, description, and pricing flags, enabling analysis of products by various characteristics. It serves as a foundational data mart component that allows business users to query and analyze product-related metrics across different product categories and attributes.
     - `/home/yosef/Desktop/intensive/jaffle-shop/models/staging/stg_products.yml`: This module defines a staging model for product data that transforms raw product information into a clean, standardized format with one row per product. It establishes product_id as a unique, non-null key field to ensure data integrity and enable reliable joins with other models in the data warehouse. The model serves as a foundational data layer that prepares product information for downstream analytics and reporting workflows.

6. **Domain:** Data Pipeline Automation
   - Module Count: 4
   - Representative Modules:
     - `/home/yosef/Desktop/intensive/jaffle-shop/.github/workflows/scripts/dbt_cloud_run_job.py`: This Python module provides programmatic control over dbt (data build tool) jobs through the dbt Cloud API. It enables triggering dbt job runs with configurable parameters like git branch and schema overrides, while monitoring job status through a mapping of integer codes to human-readable states. The module serves as an automation interface for dbt Cloud operations, allowing external systems to initiate and track data transformation workflows programmatically.
     - `/home/yosef/Desktop/intensive/jaffle-shop/.github/workflows/ci.yml`: This GitHub Actions workflow automatically triggers dbt Cloud jobs for pull requests targeting the main or staging branches, running data transformation tests across multiple database platforms (Snowflake, BigQuery, and Postgres). It sets up the environment with specific dbt Cloud job configurations, installs dependencies using uv, and executes the dbt Cloud job script to validate data transformations in isolated schemas based on the pull request branch name. The workflow serves as a continuous integration mechanism to ensure data model changes are tested across different database systems before merging, helping maintain data quality and consistency in the jaffle-shop project.
     - `/home/yosef/Desktop/intensive/jaffle-shop/.github/workflows/cd_prod.yml`: This GitHub Actions workflow automates the deployment of dbt (data build tool) projects to production environments across three different data warehouses: Snowflake, BigQuery, and PostgreSQL. When code is pushed to the main branch, it triggers parallel jobs that install dependencies, authenticate with dbt Cloud using API credentials, and execute pre-configured dbt Cloud jobs to transform and deploy data models. The workflow serves as a CI/CD pipeline that ensures consistent, automated deployment of data transformations to production data warehouses whenever changes are merged to the main branch.

### Confidence

- **Evidence Type:** heuristic
- **Confidence Score:** 0.75
- **Resolution Status:** inferred


## Question 5: What changes most often?

### Answer

Based on the evidence, the files that change most often are:

1. `/home/yosef/Desktop/intensive/jaffle-shop/.pre-commit-config.yaml:1` - This file configures pre-commit hooks and has 1 commit, making it the most frequently changed file.

2. `/home/yosef/Desktop/intensive/jaffle-shop/packages.yml:1` - This file also has 1 commit, indicating it's another high-change file.

The Pareto Analysis shows that 100% of files account for 80% of changes, with the two files above being the primary contributors to this change frequency.

For new developers, this suggests that configuration files, particularly those related to code quality and package management, are the most dynamic parts of this codebase. It's important to pay attention to changes in these files as they can significantly impact the development workflow and project dependencies.

### Evidence

1. **High-Change File:** `/home/yosef/Desktop/intensive/jaffle-shop/.pre-commit-config.yaml`
   - Commit Count: 1
   - Purpose: This module configures pre-commit hooks for a Python project to automatically enforce code quality standards before commits are finalized. It integrates multiple repositories to check YAML syntax, fix trailing whitespace and end-of-file issues, validate requirements.txt formatting, and use Ruff for Python code formatting and linting with automatic fixes. The configuration ensures consistent code quality and formatting across the development team by running these checks locally before code is pushed to version control.
   - Location: `/home/yosef/Desktop/intensive/jaffle-shop/.pre-commit-config.yaml`:1-14

2. **High-Change File:** `/home/yosef/Desktop/intensive/jaffle-shop/packages.yml`
   - Commit Count: 1
   - Location: `/home/yosef/Desktop/intensive/jaffle-shop/packages.yml`:1-7

3. **Pareto Analysis:**
   - 100.0% of files account for 80% of changes
   - High-change files: `/home/yosef/Desktop/intensive/jaffle-shop/.pre-commit-config.yaml`, `/home/yosef/Desktop/intensive/jaffle-shop/packages.yml`

### Confidence

- **Evidence Type:** heuristic
- **Confidence Score:** 1.00
- **Resolution Status:** resolved


## Coverage Summary

- **Questions Answered:** 5/5
- **Total Evidence Citations:** 29
- **Average Confidence:** 0.86
