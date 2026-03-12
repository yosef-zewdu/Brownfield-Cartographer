# RECONNAISSANCE

## What is the primary ingestion path?
The primary data ingestion path for the Jaffle Shop project is using sample data via dbt seeds. This method involves loading CSV files from the jaffle-data directory directly into a data warehouse. To implement this, an engineer must configure the seed-paths in the dbt_project.yml file and execute the dbt seed command.
The raw data consists of six CSV files in the jaffle-data directory:
raw_customers.csv - Customer information
raw_orders.csv - Order records
raw_items.csv - Order items
raw_products.csv - Product catalog
raw_stores.csv - Store locations
raw_supplies.csv - Supply records

## What are the critical outputs?
Orders mart: A core data mart table that provides the foundation for the semantic models and standardized business metrics. Orders.yml
order_items Mart: provides detailed item-level data with one row per order item, including revenue calculations, supply costs, and product categorization order_items.yml
customers Mart: delivers customer-centric analytics with lifetime spending metrics, order counts, and customer segmentation (new vs returning) customers.yml
products Mart: A dimensional reference table containing product catalog information including pricing and categorization . This serves as essential context for order and revenue analysis.
supplies Mart: Tracks supply costs and inventory components required for products, enabling cost analysis and profitability calculations .

## What is the blast radius if the most critical module fails?
The blast radius of a critical module failure would be significant due to the interconnected data pipeline and multi-platform deployment strategy.

Critical Module Identification
The most critical modules appear to be the core data marts in models/marts/, particularly:

customers - Contains customer lifetime value metrics and serves as a key dimension for analysis customers.yml
orders - Central fact table connecting customers and order items orders.yml
order_items - Detailed transaction data that feeds both orders and customers models order_items.yml

Blast Radius Analysis
If any of these core marts fail, the blast radius includes:
All Data Warehouse Platforms - The CI/CD pipeline runs parallel jobs across Snowflake, BigQuery, and Postgres ci.yml:
All Environments - Failures would affect CI (pull requests), staging, and production deployments cd_staging.yml
Semantic Models - All semantic models and metrics defined in the YAML files would become unavailable customers.yml

## Where is the business logic concentrated vs. distributed?
The business logic in the Jaffle Shop dbt project is primarily concentrated in the marts layer with additional distribution in the semantic layer for analytics definitions.

Concentrated Business Logic (Marts Layer)
The core business logic is concentrated in three main mart models:

Orders Mart (models/marts/orders.sql)
Contains complex order-level business logic including:
Order aggregation calculations (order costs, subtotals, item counts) orders.sql
Boolean flag computations for food/drink orders orders.sql
Customer order sequencing using window functions orders.sql
Order Items Mart (models/marts/order_items.sql)
Contains item-level business logic:
Supply cost aggregation by product order_items.sql
Multi-table joins combining order, product, and supply data order_items.sql
Customers Mart (models/marts/customers.sql)
Contains customer analytics logic:
Lifetime value calculations and order aggregation customers.sql
Customer type classification logic customers.sql

Distributed Business Logic (Semantic Layer)
Business logic is distributed across semantic models and metrics definitions:

Semantic Models
Define business entities, dimensions, and measures for analytics:
Orders semantic model with business dimensions and measures orders.yml
Order items semantic model with revenue calculations order_items.yml:43-87
Customers semantic model with customer lifetime metrics customers.yml:33-70
Business Metrics
Distributed business logic for KPI calculations:
Revenue growth calculations order_items.yml
Customer segmentation metrics orders.yml
Profitability calculations order_items.yml

##  What has changed most frequently in the last 90 days (git velocity map)?
 1. .pre-commit-config.yaml
      Commits: 1
  2. packages.yml
      Commits: 1
