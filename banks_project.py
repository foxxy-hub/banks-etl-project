import pandas as pd
import sqlite3
import requests
from bs4 import BeautifulSoup
from datetime import datetime



# Project settings
url = (
    "https://web.archive.org/web/20230908091635/"
    "https://en.wikipedia.org/wiki/List_of_largest_banks"
)
exchange_rate_csv = "exchange_rate.csv"
table_attribs = ["Name", "MC_USD_Billion"]
output_csv = "Largest_banks_data.csv"
db_name = "Banks.db"
table_name = "Largest_banks"
log_file = "code_log.txt"


def log_progress(message):
    timestamp = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")

    with open(log_file, "a") as file:
        file.write(f"{timestamp} : {message}\n")


def extract(url, table_attribs):
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table")

    rows = table.find_all("tr")[1:11]
    data = []

    for row in rows:
        cols = row.find_all("td")

        if len(cols) < 3:
            continue

        name = cols[1].get_text(" ", strip=True)
        market_cap = cols[2].get_text(strip=True)

        market_cap = market_cap.replace(",", "")

        data.append({
            "Name": name,
            "MC_USD_Billion": float(market_cap)
        })

    return pd.DataFrame(data, columns=table_attribs)


def transform(df, csv_path):
    rates = pd.read_csv(csv_path)
    rates = rates.set_index("Currency")["Rate"].to_dict()

    df["MC_GBP_Billion"] = (
        df["MC_USD_Billion"] * rates["GBP"]
    ).round(2)

    df["MC_EUR_Billion"] = (
        df["MC_USD_Billion"] * rates["EUR"]
    ).round(2)

    df["MC_INR_Billion"] = (
        df["MC_USD_Billion"] * rates["INR"]
    ).round(2)

    return df


def load_to_csv(df, path):
    df.to_csv(path, index=False)


def load_to_db(df, connection, table):
    df.to_sql(table, connection, if_exists="replace", index=False)


def run_queries(connection, table):
    queries = [
        f"SELECT Name, MC_GBP_Billion FROM {table};",
        f"SELECT Name, MC_EUR_Billion FROM {table};",
        f"SELECT Name, MC_INR_Billion FROM {table};"
    ]

    for query in queries:
        print(f"\nQuery: {query}")
        print(pd.read_sql(query, connection))


# Start ETL process
log_progress("Preliminaries complete. Initiating ETL process")

df = extract(url, table_attribs)
log_progress("Data extraction complete")

df = transform(df, exchange_rate_csv)
log_progress("Data transformation complete")

load_to_csv(df, output_csv)
log_progress("Data saved to CSV file")

connection = sqlite3.connect(db_name)
log_progress("SQL Database connection opened")

load_to_db(df, connection, table_name)
log_progress("Data loaded to database")

run_queries(connection, table_name)

connection.close()
log_progress("SQL Database connection closed")

print("\nETL process completed successfully.")