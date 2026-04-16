import os
import sys

# Add Odoo to path if necessary
# Assuming standard docker structure or local install
# We can use the shell directly to run an Odoo shell command

from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

# Replace with your actual database name if known, but we can try to find it
dbname = 'odoo' # Common default in docker

try:
    registry = Registry(dbname)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        dashboard = env['analysis.dashboard']
        data = dashboard.get_dashboard_data()
        print("DASHBOARD DATA RESULTS:")
        for key, value in data.items():
            if isinstance(value, dict):
                print(f"[{key}] keys: {list(value.keys())}")
            elif isinstance(value, list):
                print(f"[{key}] count: {len(value)}")
            else:
                print(f"[{key}]: {value}")
        
        # Check Workload specifically
        print("\nWORKLOAD DETAIL:")
        print(data.get('workload', []))
        
        # Check KPIs
        print("\nKPI DETAIL:")
        print(data.get('kpis', {}))

except Exception as e:
    print(f"ERROR: {e}")
