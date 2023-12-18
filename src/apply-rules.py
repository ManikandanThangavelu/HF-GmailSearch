import os
import json
import sqlite3

config_dir = os.path.abspath("config")
conn = sqlite3.connect(f"{config_dir}/emails.db")


def fetch_rules():
    with open(f"{config_dir}/rules.json", 'r') as f:
        data = json.load(f)
    return data


def generate_sql_query(root_predicate, rules, actions):
    # Define the base SQL query
    base_query = "UPDATE emails SET "

    # Generate the SET clause based on the actions
    set_operations = []
    for action in actions:
        if action["action"] == 'Mark as':
            status = action["field"]
            set_operations.append(f"status = '{status}'")
        elif action["action"] == 'Move Message':
            mailbox_type = action["field"]
            set_operations.append(f"mailbox = '{mailbox_type}'")

    set_clause = ", ".join(set_operations)

    # Generate the WHERE clause based on the rules
    conditions = []
    for rule in rules:
        field = rule["field"]
        predicate = rule["predicate"]
        value = rule["value"]

        # Handle string type fields
        if predicate in ["contains", "does not contain", "equals", "does not equal"]:
            if predicate == "contains":
                condition = f"{field} LIKE '%{value}%'"
            elif predicate == "does not contain":
                condition = f"{field} NOT LIKE '%{value}%'"
            elif predicate == "equals":
                condition = f"{field} = '{value}'"
            elif predicate == "does not equal":
                condition = f"{field} != '{value}'"
        # Handle date type field (Received) - Less than / Greater than for days / months
        elif predicate in ["less than", "greater than"]:
            operator = "<" if predicate == "less than" else ">"
            condition = f"{field} {operator} DATE('now', '-{value} days')"
        else:
            raise ValueError(f"Invalid predicate: {predicate}")
        conditions.append(condition)

    # Join conditions based on the root_predicate
    if root_predicate == "ALL":
        where_clause = " AND ".join(conditions)
    elif root_predicate == "ANY":
        where_clause = " OR ".join(conditions)
    else:
        raise ValueError("Invalid root_predicate. Use 'ALL' or 'ANY'.")
    # Concatenate the base query, SET clause, and WHERE clause
    full_query = f"{base_query} {set_clause} WHERE {where_clause}"
    return full_query


def run_query(sql_query):
    cursor = conn.cursor()
    cursor.execute(sql_query)
    conn.commit()


def apply_rules(rules):
    for rule in rules:
        print(f"Applying rule - {rule['id']}")
        sql_query = generate_sql_query(rule['root_predicate'], rule["rules"], rule["actions"])
        print(f"Query - {sql_query}")
        run_query(sql_query)


def main():
    rules = fetch_rules()
    apply_rules(rules)


if __name__ == '__main__':
    main()
    conn.close()
