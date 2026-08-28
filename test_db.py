from sqlalchemy import text

from app.db.database import engine


def test_database():

    with engine.connect() as connection:

        result = connection.execute(
            text("SELECT version();")
        )

        version = result.scalar()

        print("資料庫連線成功！")
        print(version)


if __name__ == "__main__":
    test_database()