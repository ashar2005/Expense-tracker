## Perfective Maintenance Report (Member B)

### Refactoring & Code Quality Enhancements
* **Target File:** `Backend/validators.py` & `Backend/models.py`
* **Maintainability Index:** Improved from **86.1 to 89.4 (Grade A)**

#### Key Refactoring Achievements:
1. **DRY Principle (Don't Repeat Yourself):** Centralized floating-point currency parsing into a single reusable helper function `parse_and_validate_amount()`. Eliminated redundant inline checks across endpoints.
2. **Type Annotations:** Applied Python `typing` hint definitions (`Union`, `Tuple`, `dict[str, Any]`) across validator utilities to support automated static analysis and IDE autocomplete.
3. **Docstring Standard:** Added standardized PEP 257 compliant docstrings to all refactored business functions.


# Phase 5: Lehman’s Laws of Software Evolution Analysis

## Overview
Lehman’s Laws describe the dynamics of E-type (evolutionary) software systems over time. Below is an analysis of how ExpenseMate conforms to these fundamental software engineering laws throughout its maintenance lifecycle.

---

### 1. Law I: Continuing Change (1974)
> *"An E-type system must be continually adapted or it becomes progressively less satisfactory."*

* **Application to ExpenseMate:** ExpenseMate was initially built for standard local currency expense logging. To remain practical and relevant for users across different regions, adaptive maintenance was performed to introduce the **Multi-Currency Converter API (`/api/convert`)** and dynamic frontend exchange switching (USD, EUR, GBP, PKR). Without these additions, the application would fail to meet evolving user needs.

---

### 2. Law II: Increasing Complexity (1974)
> *"As an E-type system evolves, its complexity increases unless work is done to maintain or reduce it."*

* **Application to ExpenseMate:** As core features like CSV import/export, budget alert thresholds, and currency calculations were added, duplicate payload parsing and inline validation checks spread across multiple Flask routes. To prevent technical debt and rising complexity, perfective refactoring was performed on `Backend/validators.py` to extract a centralized sanitizer (`parse_and_validate_amount()`), keeping code complexity low (**Radon CC Grade A**).

---

### 3. Law III: Self-Regulation (1974)
> *"Global system evolution processes display self-regulating behavior."*

* **Application to ExpenseMate:** Project attributes—such as bug discovery rates, test case coverage (`tests/test_integration_system.py`), and commit activity—stayed balanced. Corrective maintenance addressing database thread locks and null aggregation checks naturally followed intense feature integration phases to stabilize product releases.

---

### 4. Law VI: Continuing Growth (1980)
> *"The functional content of an E-type system must be continually increased to maintain user satisfaction over its operational life."*

* **Application to ExpenseMate:** The system continuously grew from a minimal CLI database script into a full-stack REST application with interactive charting, automated monthly summaries, threshold alerting, and CSV data streaming.

---

### 5. Law VII: Declining Quality (1996)
> *"The quality of an E-type system will appear to decline unless rigorously maintained and adapted to operational environment changes."*

* **Application to ExpenseMate:** When database schemas expanded, edge cases emerged (e.g., empty query results causing `NoneType` errors). Corrective maintenance was performed to add fallback mechanisms (`float(val or 0.0)`) and strict parameter type hints (`Union`, `Tuple`), maintaining a high **Maintainability Index score (89.4 / 100, Grade A)**.