"""
Generates realistic sample datasets for testing and initial demonstration:
1. sales_data.xlsx (Multi-sheet: Orders, Returns, Customers)
2. employees_data.csv
3. inventory_data.xlsx (Multi-sheet: Current_Stock, Suppliers)
"""

import pandas as pd
import numpy as np
from pathlib import Path

SAMPLES_DIR = Path(__file__).resolve().parent

def generate_samples():
    SAMPLES_DIR.mkdir(exist_ok=True)

    # 1. Sales Dataset (Multi-sheet Excel)
    orders_df = pd.DataFrame({
        "Order_ID": ["ORD-1001", "ORD-1002", "ORD-1003", "ORD-1004", "ORD-1005", "ORD-1005", "ORD-1006", "ORD-1007"],
        "Customer_Name": ["Acme Corp ", "Globex", "Initech", "Umbrella  Corp", "Stark Ind", "Stark Ind", " Wayne Enterprises", "Cyberdyne"],
        "Region": ["North", "South", "north", "East", "West", "West", "south", "East"],
        "Order_Date": ["2026-01-15", "2026-01-16", "2026-01-18", "invalid_date", "2026-02-01", "2026-02-01", "2026-02-05", "2026-02-10"],
        "Sales_Amount": [1250.50, 430.00, None, 8900.00, 310.25, 310.25, 45000.00, 150.00],  # 45000 is potential outlier
        "Quantity": [10, 4, 2, 50, 3, 3, 100, 1],
        "Discount": [0.05, 0.0, 0.10, 0.15, None, None, 0.20, 0.0],
    })

    returns_df = pd.DataFrame({
        "Return_ID": ["RET-501", "RET-502", "RET-503"],
        "Order_ID": ["ORD-1002", "ORD-1004", "ORD-1006"],
        "Reason": ["Defective item", "Wrong size", "Customer cancellation"],
        "Refund_Amount": [430.00, 8900.00, 45000.00]
    })

    customers_df = pd.DataFrame({
        "Customer_ID": ["CUST-01", "CUST-02", "CUST-03", "CUST-04", "CUST-05"],
        "Company": ["Acme Corp", "Globex", "Initech", "Umbrella Corp", "Stark Ind"],
        "Contact_Email": ["info@acme.com", "sales@globex.org", "contact@initech.io", None, "tony@stark.com"],
        "Tier": ["Gold", "Silver", "Bronze", "Platinum", "Gold"]
    })

    sales_path = SAMPLES_DIR / "sales_data.xlsx"
    with pd.ExcelWriter(sales_path, engine="openpyxl") as writer:
        orders_df.to_excel(writer, sheet_name="Orders", index=False)
        returns_df.to_excel(writer, sheet_name="Returns", index=False)
        customers_df.to_excel(writer, sheet_name="Customers", index=False)

    # 2. Employees Dataset (CSV)
    employees_df = pd.DataFrame({
        "Emp_ID": ["EMP-001", "EMP-002", "EMP-003", "EMP-004", "EMP-005", "EMP-006", "EMP-007"],
        "Full_Name": ["Alice Johnson", "Bob Smith", "Charlie Brown ", "Diana Prince", "Evan Wright", "Fiona Gallagher", "George Clark"],
        "Department": ["Engineering", "engineering", "HR", "Finance", "Sales", "Engineering", "Marketing"],
        "Salary": [95000, 88000, 62000, 105000, None, 92000, 71000],
        "Hire_Date": ["2023-03-15", "2022-07-01", "2024-01-10", "2021-11-20", "2025-05-04", "2023-09-12", "invalid-date"],
        "Performance_Rating": [4.5, 3.8, 4.0, 4.9, 3.2, 4.1, None],
        "Remote": [True, True, False, False, True, False, True]
    })
    employees_path = SAMPLES_DIR / "employees_data.csv"
    employees_df.to_csv(employees_path, index=False)

    # 3. Inventory Dataset (Excel)
    stock_df = pd.DataFrame({
        "SKU": ["SKU-A100", "SKU-B200", "SKU-C300", "SKU-D400", "SKU-E500", "SKU-E500"],
        "Product_Name": ["Industrial Bolt 10mm", "Steel Washer M8", "Hex Nut 10mm", "Titanium Screw 25mm", "Copper Gasket", "Copper Gasket"],
        "Category": ["Fasteners", "Washers", "Fasteners", "Specialty", "Gaskets", "Gaskets"],
        "Unit_Cost": [0.45, 0.12, 0.35, 12.50, 2.10, 2.10],
        "In_Stock": [5000, 12000, 4500, 250, None, None],
        "Reorder_Level": [1000, 2000, 1000, 100, 300, 300]
    })

    suppliers_df = pd.DataFrame({
        "Supplier_ID": ["SUP-01", "SUP-02", "SUP-03"],
        "Supplier_Name": ["Apex Industrial Hardware", "Global Metals LLC", "Precision Fasteners"],
        "Rating": [4.8, 4.2, 4.6],
        "Lead_Time_Days": [7, 14, 5]
    })

    inventory_path = SAMPLES_DIR / "inventory_data.xlsx"
    with pd.ExcelWriter(inventory_path, engine="openpyxl") as writer:
        stock_df.to_excel(writer, sheet_name="Current_Stock", index=False)
        suppliers_df.to_excel(writer, sheet_name="Suppliers", index=False)

    print("Sample datasets successfully created in:", SAMPLES_DIR)

if __name__ == "__main__":
    generate_samples()
