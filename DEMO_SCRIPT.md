# CARTIVANTA — Recruiter & Interviewer Demo Script

> **Product Presentation, Technical Walkthrough & Architecture Guide**  
> *Commercial Retail Operating System for Indian Supermarkets & Retail Stores*

---

## 1. 60-Second Elevator Pitch

> *"Hello, I'm showcasing **CARTIVANTA**, an integrated retail shop management, POS billing, and business intelligence platform designed specifically for small-to-medium retail stores such as supermarkets, grocery stores, and provision shops.*  
>
> *Unlike generic demo dashboards with hardcoded numbers, CARTIVANTA is built as a complete commercial retail operating system. It features a sub-second POS billing counter with barcode scanning, automated GST computation, and thermal receipt printing; a live inventory tracking engine with low-stock reorder thresholds and movement audit trails; a digital Khata credit ledger for customer Udhaar management; an operating expense and true P&L reconciliation engine; a flexible discount and promotional offers system; and a data-driven business intelligence dashboard operating consistently in Indian Rupee (₹).*  
>
> *Let me walk you through the platform."*

---

## 2. Guided Feature Walkthrough

### Stop 1: Daily Shop Overview (`http://127.0.0.1:8000/`)
- **Key Point**: Transparent, single-glance store performance for the shopkeeper.
  > *"Every metric here is computed directly from live transactional records. Today's sales, estimated gross profit, total customer visits, pending Udhaar balance, and supplier dues give the shopkeeper complete financial clarity in seconds. Role protection ensures cashiers see daily bill counts and sales without exposing confidential purchase costs and net margins."*

### Stop 2: High-Speed POS Counter & Thermal Billing (`/billing`)
- **Key Point**: Real-world counter speed with keyboard shortcuts and GST calculations.
  > *"The billing counter supports instant barcode scanning, live product search, active discount offer selection, custom quick discounts, and multiple payment modes (Cash, UPI, Card, and Khata/Udhaar). Post-discount taxable amounts are automatically computed before applying GST rates, and a clean thermal receipt is generated with immutable audit records."*

### Stop 3: Products Catalog & Inventory Valuation (`/products` and `/stock`)
- **Key Point**: Real-time stock audit, FIFO valuation, and low-stock warnings.
  > *"Stock levels adjust dynamically with each bill created, purchase invoice received, or return processed. Low-stock thresholds trigger prioritized reorder recommendations directly linked to supplier contact details."*

### Stop 4: Purchases & Supplier Dues (`/purchases`)
- **Key Point**: Inward invoice management and supplier payable tracking.
  > *"Shopkeepers can log inward wholesale shipments, update cost prices, record partial payments, and track outstanding supplier balances."*

### Stop 5: Customer Khata Ledger & Udhaar (`/customers`)
- **Key Point**: Built-in digital credit ledger for neighborhood retail trust.
  > *"Store owners can track credit balances customer-by-customer, record partial repayments, and view timestamped account statements."*

### Stop 6: Operating Expenses & Net Real Profit (`/expenses`)
- **Key Point**: True bottom-line P&L financial statement.
  > *"Gross sales minus purchase cost yields Gross Profit. When daily shop expenses (rent, electricity, salaries, transport) are deducted, the system calculates true Net Operating Profit."*

### Stop 7: Discounts & Offers Manager (`/discounts`)
- **Key Point**: Controlled, profitable promotional campaigns.
  > *"Shopkeepers can create percentage or flat ₹ discounts, apply them storewide or to specific categories/products, and enforce minimum bill amounts and maximum discount caps."*

### Stop 8: Business Insights & Planning (`/insights`)
- **Key Point**: Predictive commerce and historical demand planning in INR (₹).
  > *"Provides 24-month sales trajectory patterns, customer buying habit groups, expected product demand, and an interactive discount margin impact calculator to prevent profit-destroying promotions."*

---

## 3. High-Value Technical Interview Questions & Answers

### Q1: "How did you design the database architecture for data consistency and performance?"
> **Answer**: *"I implemented a dual-engine architecture with SQLAlchemy, supporting both SQLite in WAL (Write-Ahead Logging) mode for zero-configuration local deployment and PostgreSQL for multi-counter concurrency. All financial transactions—including bill creation, stock deduction, and Khata credit changes—run inside atomic database transactions to eliminate partial writes or corrupted inventory levels."*

### Q2: "How are discounts and GST taxes calculated in the billing flow?"
> **Answer**: *"In Indian retail accounting, discounts must reduce the taxable value of products before calculating GST to prevent tax overcharges. The billing engine calculates: `taxable_line = line_gross * (1 - discount_pct)`, applies category-specific GST rates to the post-discount taxable amount, and stores immutable snapshot copies of the discount name, rate, and amount on the completed bill so historical accounting records remain unchanged if promotions are later modified."*

### Q3: "How is security and role-based access enforced across the platform?"
> **Answer**: *"The platform enforces role-based authorization between Owner and Cashier roles. Cashiers can operate billing, look up items, check available stock, and register customer visits. They are strictly blocked via route guards and template conditionals from viewing purchase costs, unit profit margins, supplier payment balances, operating expenses, and executive P&L statements."*
