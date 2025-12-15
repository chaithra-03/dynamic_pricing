# Dynamic Pricing & Flash Sale Management System

This project is a **backend system for product management, dynamic pricing, and flash sales** built using **FastAPI**, **SQLAlchemy**, and **Python**.  
It focuses on **price optimization**, **controlled flash sale purchases**, and **analytics-driven insights**.

---

## 1. Project Overview

The system manages **products with full CRUD operations**, supports **dynamic pricing rules**, enables **flash sale lifecycle management**, and provides **analytics** to evaluate business performance.

Key goals of the project:
- Track product price changes over time
- Dynamically calculate prices based on pricing rules
- Handle high-demand flash sales safely and consistently
- Provide analytics such as conversion rate, elasticity, and revenue trends

---

## 2. Features

###  Product Management
- Full **CRUD operations** for products
- Price attributes:
  - Base price
  - Current price
  - Minimum allowed price
  - Cost price
- **Price history tracking** for every price change
- **Pagination** for efficient price history retrieval

---

###  Dynamic Pricing Engine
Pricing rules can be created and applied **per product**, including:

- **Time-based pricing** (specific time windows)
- **Quantity-based pricing** (bulk purchase discounts)
- **User-tier-based pricing** (pricing based on user classification)
- Rule priority handling
- Minimum price enforcement to prevent loss-making prices

A **cache layer** is used during price calculation to reduce repeated computation and improve response time.

---

###  Flash Sale Management
- Full **CRUD operations** for flash sales
- Flash sale lifecycle states:
  - `scheduled`
  - `active`
  - `ended`
- Ability to associate multiple products with a flash sale
- Configuration options:
  - Flash sale price
  - Allocated stock
  - Remaining stock
  - **Per-user purchase limits per product**
- Concurrency-safe stock updates to prevent overselling

---

###  Flash Sale Purchase Flow
- Background tasks used for purchase processing
- Server-side price validation to prevent manipulation
- Atomic stock deduction
- Per-user purchase limit enforcement
- Purchase summary tracking per user

---

###  Analytics & Insights
The system provides analytics for flash sales, including:

- **Conversion rate**
- **Price elasticity**
- **Units sold**
- **Total revenue**
- **Per-day revenue**
- **Peak purchase time analysis**

These insights help evaluate:
- Pricing strategy effectiveness
- User purchasing behavior
- Flash sale performance

---

###  Authentication & Authorization
- **Role-based authentication** is implemented
- Supported roles include:
  - `admin`
  - `user`
- Admin-only access is enforced for:
  - Product creation and updates
  - Pricing rule management
  - Flash sale creation and lifecycle control
  - System metrics and analytics endpoints
- Token-based authentication using a configurable secret and algorithm

---

## 3. Tech Stack

- **Python**
- **FastAPI**
- **SQLAlchemy ORM**
- **SQLite** 
- **Pydantic v2**
- **Pytest**

---

## 4. Dependencies

Install all required dependencies using:

`pip install -r requirements.txt`

---

## 5. How to Run the Application
### Clone the Repository

`git clone https://github.com/<your-username>/<repository-name>.git`

`cd <repository-name>`

### Create and Activate Virtual Environment
`python -m venv venv`

`venv\Scripts\activate`        ( Windows )

`-source venv/bin/activate`   ( macOS/Linux )

### Configure Environment Variables

Create a .env file in the project root:

`DATABASE_URL=sqlite:///./app.db`

`SECRET_KEY=your_secret_key`

`ALGORITHM=HS256`

`ACCESS_TOKEN_EXPIRE_MINUTES=60`

### Start the Server
`uvicorn app.main:app --reload`


### Available endpoints:

Swagger UI: http://127.0.0.1:8000/docs

OpenAPI Spec: http://127.0.0.1:8000/openapi.json

---

## 6. Running Tests

The project uses pytest with an in-memory SQLite database for isolation and speed.

`python -m pytest`

### Test Coverage Includes:

- Product creation and retrieval

- Pricing rule application

- Final price calculation

- Flash sale creation and activation

- Flash sale purchase flow and per-user limits

---

## 7. Assumptions

- All timestamps are treated as UTC

- Cache is in-memory and process-local

- Authentication is role-based and token-driven

- Flash sale purchase tests are executed at the service layer (not HTTP level)
