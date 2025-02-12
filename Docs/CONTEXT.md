# Personal Finance Tracker Website Specification

This document provides a structured overview of the Personal Finance Tracker website’s user flow, features, and functionalities. It is intended to guide developers in understanding and implementing each aspect of the system.

---

## Tech Stack:
- **Frontend**:
  - **HTML, CSS, JavaScript** for structure and interactivity.
  - **AJAX** for asynchronous data fetching to enhance user experience.
- **UI Framework**:
  - **Tailwind CSS** for utility-first styling.
  - **Flowbite** for prebuilt, accessible UI components.
- **Backend**:
  - **Flask (Python)** for server-side logic, routing, and data processing.
- **Database**:
  - **SQLite** for a lightweight, file-based relational database solution.



## 1. Landing/Home Page (Unauthenticated Users)

### Hero Section

- **Tagline:** A clear, concise statement such as “Take Control of Your Finances.”
- **Call-to-Action (CTA) Buttons:**
  - **Sign Up:** Leads to the registration flow.
  - **Login:** Navigates to the login form.

### Key Features

- **Budgeting Tools:** Highlight how users can set and manage budgets.
- **Expense Tracking:** Emphasise easy transaction management.
- **Reporting:** Mention visual reports and analytics.
- **Testimonials:** Showcase brief quotes from satisfied users.

### Footer

- **Links:**  
  - About  
  - Contact  
  - Privacy Policy  
  - Terms of Service  
- **Copyright:** Placeholder for relevant details.

---

## 2. Navigation Bar (Authenticated Users)

Once a user logs in, the navigation bar updates to give access to core features:

- **Logo:** Clicking it returns to the main dashboard.
- **Menu Items:**
  - **Dashboard:** Financial overview.
  - **Transactions:** List of all income and expenses.
  - **Budgets:** Manage spending limits per category.
  - **Reports:** View analytics and visualisations.
  - **Account:** Profile settings and account-specific operations.

### Quick Actions (Floating or Static)

- **Add Transaction (`+`)**: Prominently placed button to quickly record a new transaction.
- **Search Bar:** Allows users to search transactions by description, category, or tags.

---

## 3. Dashboard (Default View After Login)

The Dashboard serves as a succinct overview of the user’s financial status.

### 3.1 Summary Cards

- **Current Balance:** Shows total income minus total expenses.
- **Monthly Income vs. Expenses:** A comparison bar (or chart) for the current month.
- **Net Savings Trend:** A line chart indicating savings growth over time.

### 3.2 Recent Transactions

Displays the last 5–10 transactions in reverse chronological order:
- Date  
- Category  
- Amount  

**View All:** Links to the main Transactions page for in-depth review.

### 3.3 Budget Progress

Show top 3–5 most relevant categories:
- **Category Name** (e.g., Groceries, Rent)
- **Spent vs. Budget** (e.g., “£200 / £500”)
- **Graphical element** (e.g., progress bar or circular gauge) indicating how close the user is to the limit.

---

## 4. Transactions Page

This page displays a comprehensive view of income and expense records and offers multiple ways to organise and manage them.

### 4.1 Filters

- **Date Range:** From–to for filtering transactions.
- **Type:** Income or Expense.
- **Category:** E.g., Food, Rent, Utilities.
- **Tags:** Optional custom labels.

### 4.2 Table/List View

**Columns:**
- Date
- Description
- Category
- Amount (positive for income, negative for expenses or distinct colour)
- Actions (Edit / Delete)

**Sorting:** Clickable headers to sort by date or amount.

### 4.3 Add Transaction

- **Button:** Either a floating action button or a visible button.

**Add Transaction Modal/Form:**
- Type (Income/Expense)
- Amount
- Date
- Category (dropdown list)
- Description (text)
- Tags (optional; user-defined labels)
- Recurring Toggle (e.g., “Repeat monthly”)

---

## 5. Budgets Page

Here, users can create and manage budget limits to keep spending in check.

### 5.1 Monthly Budget Overview

- **Total Budget vs. Remaining:** High-level summary of all budgets combined.
- **Time Period Selector** (optional if needed to show weekly, monthly, annual budgets).

### 5.2 Category-Specific Budgets

**Category Card/List:**
- **Category Icon** (optional for visual clarity)
- **Budget Limit** (e.g., £500 for Groceries)
- **Current Spending** (accumulated expenses so far)
- **Progress Bar** indicating how much of the budget is used.
- **Edit Budget** button to update the category’s limit or timeframe.

### 5.3 Add New Budget

**Form Fields:**
- Category (dropdown)
- Budget Limit (numeric input)
- Timeframe (e.g., monthly, weekly)
- Submit/Save to finalise.

---

## 6. Reports/Analytics Page

Gives users a holistic view of their finances through various charts and data summaries.

### 6.1 Timeframe Selector

- **Preset Ranges:** Week, Month, Year.
- **Custom Range:** User-defined start and end dates.

### 6.2 Visualisations

- **Pie Chart:** Spending breakdown by category for the selected timeframe.
- **Bar Chart:** Monthly (or weekly) income vs. expenses comparison.
- **Trend Line:** Tracks net savings or cash flow trend over time.

### 6.3 Export Options

- **PDF/CSV:** Generate sharable or downloadable reports in multiple formats.

---

## 7. Account Section

A dedicated area for managing personal information, preferences, and security.

### 7.1 Profile

- Edit Name, Email, Profile Picture: Basic user information.

### 7.2 Settings

- Currency (GBP, EUR, USD, etc.)
- Date Format (DD/MM/YYYY, etc.)
- Timezone
- **Dark Mode Toggle** to switch between light/dark themes.

### 7.3 Security

- Change Password
- Two-Factor Authentication (2FA)
- Notifications (email or SMS alerts for certain account activities)

### 7.4 Data Management

- **Import (CSV/Bank Sync):** Option to import transaction data from external sources.
- **Export (CSV/JSON):** Download all user data in a structured format.
- **Delete Account:** Permanently remove user data (with confirmation).

### 7.5 Logout

Securely end the session and return to the landing page.

---

## 8. Security & Validation

### 8.1 HTTPS

All pages secured via HTTPS to protect user data in transit.

### 8.2 Input Validation

- **Transaction Fields:** Must be valid numbers, categories must exist, etc.
- **Duplicate Checking:** Option to warn users if they input duplicates.
- **Confirmation Dialogues:** For critical actions such as deleting a transaction or account.

---

## 9. Userflow Diagram Summary

```mermaid
flowchart LR
    A[Landing Page] -->|Sign Up/Login| B[Dashboard]
    B --> C[Transactions]
    B --> D[Budgets]
    B --> E[Reports]
    B --> F[Account]

    C -->|Add/Edit/Delete| C
    D -->|Add/Edit Budget| D
    F -->|Profile/Settings/Security| F

## 10. Database Schema

### 10.1 Users Table

| Field         | Type                 | Description                                  |
|---------------|----------------------|----------------------------------------------|
| **id**        | INT (PK, Auto-Inc)  | Unique identifier for each user              |
| **name**      | VARCHAR             | User’s full name                             |
| **email**     | VARCHAR (Unique)    | User’s email address                         |
| **password_hash** | VARCHAR         | Password hash for secure storage             |
| **currency**  | VARCHAR (10)        | Preferred currency (e.g. GBP, EUR, USD)      |
| **date_format** | VARCHAR (10)      | Preferred date format (e.g. DD/MM/YYYY)      |
| **timezone**  | VARCHAR (50)        | Timezone (e.g. Europe/London)                |
| **created_at**| DATETIME            | Record creation timestamp                     |
| **updated_at**| DATETIME            | Last update timestamp                         |

---

### 10.2 Categories Table

| Field         | Type                 | Description                                  |
|---------------|----------------------|----------------------------------------------|
| **id**        | INT (PK, Auto-Inc)  | Unique identifier for each category          |
| **user_id**   | INT (FK)            | References `users.id`                        |
| **name**      | VARCHAR             | Category name (e.g. Groceries, Rent)         |
| **created_at**| DATETIME            | Record creation timestamp                     |
| **updated_at**| DATETIME            | Last update timestamp                         |

---

### 10.3 Transactions Table

| Field         | Type                      | Description                                           |
|---------------|---------------------------|-------------------------------------------------------|
| **id**        | INT (PK, Auto-Inc)       | Unique identifier for each transaction               |
| **user_id**   | INT (FK)                 | References `users.id`                                |
| **date**      | DATE/DATETIME            | Date or datetime of the transaction                  |
| **type**      | ENUM('income','expense') | Defines whether the entry is income or expense       |
| **category_id** | INT (FK)               | References `categories.id`                           |
| **amount**    | DECIMAL(10,2)            | Financial amount                                     |
| **description** | VARCHAR (255)          | Text description of the transaction                  |
| **tags**      | VARCHAR (255)            | Comma-separated or JSON array of tags (optional)     |
| **recurring** | TINYINT(1)               | Indicates if transaction repeats                     |
| **created_at**| DATETIME                 | Record creation timestamp                            |
| **updated_at**| DATETIME                 | Last update timestamp                                |

---

### 10.4 Budgets Table

| Field         | Type                 | Description                                         |
|---------------|----------------------|-----------------------------------------------------|
| **id**        | INT (PK, Auto-Inc)  | Unique identifier for each budget                   |
| **user_id**   | INT (FK)            | References `users.id`                              |
| **category_id** | INT (FK)          | References `categories.id`                         |
| **limit_amount** | DECIMAL(10,2)    | Budget limit for the category                      |
| **timeframe** | VARCHAR (50)        | e.g. 'monthly', 'weekly', 'yearly'                 |
| **start_date** | DATE               | Budget start date (optional if always monthly)      |
| **end_date**   | DATE               | Budget end date (optional if always monthly)        |
| **created_at** | DATETIME           | Record creation timestamp                           |
| **updated_at** | DATETIME           | Last update timestamp                               |
