from os import getenv
from dotenv import load_dotenv
load_dotenv()

def get_db_url() -> str:
    db_driver = getenv("DB_DRIVER", "postgresql+psycopg")
    db_user = getenv("DB_USER")
    db_pass = getenv("DB_PASSWORD")
    db_host = getenv("DB_HOST")
    db_port = getenv("DB_PORT")
    db_database = getenv("DB_NAME")

    print(db_driver, db_user, db_pass, db_host, db_port, db_database)
    return "{}://{}{}@{}:{}/{}".format(
        db_driver,
        db_user,
        f":{db_pass}" if db_pass else "",
        db_host,
        db_port,
        db_database,
    )
