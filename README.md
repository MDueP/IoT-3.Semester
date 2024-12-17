Repository for IoT 3.SemesterProjekt

Venv create:
    make a .venv either from cli or by using VScode
    IMPORTANT that the name is .venv for the environment folder so it doesn't get comitted to git
    pip install -r requirements.txt
    sudo PYTHONPATH=$PYTHONPATH python3 app.py
Example for .env file - 
    FLASK_APP_KEY= "densupermegahemmeligekodesomflaskbruger"
    MYSQL_HOST = "localhost"
    MYSQL_USER = "root"
    MYSQL_PASSWORD = "keadb2024"
    MYSQL_DB = "iot3webapp"