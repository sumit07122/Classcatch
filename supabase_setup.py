"""
ClassCatch - Database Initializer
==================================
This file redirects to `init_db.py` which supports Neon.tech, Supabase,
and any standard PostgreSQL instance.
"""

from init_db import setup_database

if __name__ == '__main__':
    setup_database()
