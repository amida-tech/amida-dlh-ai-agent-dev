#!/usr/bin/env python3
"""
Test file for GitHub Code Review Agent
This file intentionally contains various code issues for the AI to identify
"""

import os
import sqlite3
import hashlib

# Security Issue: Hardcoded credentials
DATABASE_PASSWORD = "admin123"
API_KEY = "sk-1234567890abcdef"

def unsafe_sql_query(user_id):
    """
    Security Issue: SQL Injection vulnerability
    """
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # VULNERABILITY: Direct string concatenation allows SQL injection
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    
    results = cursor.fetchall()
    conn.close()
    return results

def weak_password_hash(password):
    """
    Security Issue: Weak hashing algorithm
    """
    # SECURITY FLAW: MD5 is cryptographically broken
    return hashlib.md5(password.encode()).hexdigest()

def inefficient_loop():
    """
    Performance Issue: Inefficient algorithm
    """
    data = []
    
    # PERFORMANCE ISSUE: Growing list in loop is inefficient
    for i in range(10000):
        result = []
        for j in range(i):
            result.append(j * j)
        data.append(result)
    
    return data

def missing_error_handling(filename):
    """
    Quality Issue: No error handling
    """
    # QUALITY ISSUE: File operations should have error handling
    with open(filename, 'r') as f:
        content = f.read()
    
    return content.upper()

class BadNaming:
    """
    Style Issue: Poor naming conventions
    """
    def __init__(self):
        self.a = 10  # Bad variable name
        self.b = 20  # Bad variable name
    
    def f(self, x):  # Bad function name
        """Poor function with no docstring details"""
        return self.a + self.b + x

def unused_variables():
    """
    Quality Issue: Unused variables
    """
    important_data = [1, 2, 3, 4, 5]
    unused_var = "this is never used"
    another_unused = 42
    
    # Only using one variable
    return sum(important_data)

# Quality Issue: No main guard
print("This code runs when imported!")
result = inefficient_loop()
print(f"Computed {len(result)} items")