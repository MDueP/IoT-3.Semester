import mysql.connector
import pandas as pd
import os
import dotenv
absolutepath = os.path.dirname(os.path.abspath(__file__))
os.chdir(absolutepath)
dotenv.load_dotenv()


# Udregning af Threshold for accelerometeren
conn = mysql.connector.connect(
    host=os.getenv("MYSQL_HOST"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DB")
)

query = "SELECT gyro_x, gyro_y, gyro_z FROM gyrodata"
data = pd.read_sql_query(query, conn)

print(data.head())

data = data.applymap(lambda x: x.strip() if isinstance(x, str) else x)

data = data.apply(pd.to_numeric)

mean_x = data['gyro_x'].mean()
mean_y = data['gyro_y'].mean()
mean_z = data['gyro_z'].mean()

std_x = data['gyro_x'].std()
std_y = data['gyro_y'].std()
std_z = data['gyro_z'].std()

print(f'Mean values: GyroX={mean_x}, GyroY={mean_y}, GyroZ={mean_z}')
print(f'Standard deviation values: GyroX={
      std_x}, GyroY={std_y}, GyroZ={std_z}')

conn.close()
