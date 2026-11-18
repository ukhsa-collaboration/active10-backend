import calendar
import os
from datetime import UTC, datetime

from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

load_dotenv()

engine = create_engine(
    "postgresql+psycopg://{}:{}@{}:{}/{}".format(
        os.getenv("DB_USER"),
        os.getenv("DB_PASS"),
        os.getenv("DB_HOST"),
        os.getenv("DB_PORT"),
        os.getenv("DB_NAME"),
    )
)

temp_table_name = "temp_activities"


def get_partition_name_from_unix(unix_month_start: int) -> str:
    """Generates partition table name based on the Unix timestamp for the start of the month."""
    return f"activities_{datetime.fromtimestamp(unix_month_start).strftime('%Y_%m')}"


def create_temp_table():
    """
    Creates a temporary table to store data before moving it to the partition table.
    """
    with Session(engine) as db:
        db.execute(
            text(f"CREATE TABLE IF NOT EXISTS {temp_table_name} (LIKE activities INCLUDING ALL)")
        )
        db.commit()
        print("Created temp table: ", temp_table_name)


def move_data_to_temp_table(start_date_unix, end_date_unix):
    """
    Moves data from the activities table to the temp table.
    """
    with Session(engine) as db:
        db.execute(
            text(
                f"INSERT INTO {temp_table_name} SELECT * FROM activities WHERE date >= {start_date_unix} AND date <= {end_date_unix}"  # noqa: E501
            )
        )
        db.commit()
        print("Moved data to temp table")


def delete_data_from_default_partition(start_date_unix, end_date_unix):
    """
    Deletes data from the default partition.
    """
    with Session(engine) as db:
        db.execute(
            text(
                f"DELETE FROM activities WHERE date >= {start_date_unix} AND date <= {end_date_unix}"  # noqa: E501
            )
        )
        db.commit()
        print("Deleted data from default partition")


def create_partition_and_migrate_data(partition_name, start_date_unix, end_date_unix):
    """
    Creates a partition table and moves data from the temp table to the partition table.
    """
    with Session(engine) as db:
        db.execute(
            text(
                f"CREATE TABLE IF NOT EXISTS {partition_name} PARTITION OF activities FOR VALUES FROM ({start_date_unix}) TO ({end_date_unix})"  # noqa: E501
            )
        )
        db.commit()
        print("Created partition table: ", partition_name)

        db.execute(
            text(
                f"INSERT INTO {partition_name} SELECT * FROM {temp_table_name} where date >= {start_date_unix} AND date <= {end_date_unix}"  # noqa: E501
            )
        )
        db.commit()
        print("Moved data to partition table: ", partition_name)


def delete_temp_table():
    """
    Deletes the temporary table.
    """
    with Session(engine) as db:
        db.execute(text(f"DROP TABLE IF EXISTS {temp_table_name}"))
        db.commit()
        print("Deleted temp table: ", temp_table_name)


def create_partition_table(partition_name, start_date_unix, end_date_unix):
    """
    Creates a partition table.
    """
    with Session(engine) as db:
        db.execute(
            text(
                f"CREATE TABLE IF NOT EXISTS {partition_name} PARTITION OF activities FOR VALUES FROM ({start_date_unix}) TO ({end_date_unix})"  # noqa: E501
            )
        )
        db.commit()


def migrate_data_to_partition_table(partition_name, start_date_unix, end_date_unix):
    """
    Moves data from the temp table to the partition table.
    """
    with Session(engine) as db:
        db.execute(
            text(
                f"INSERT INTO {partition_name} SELECT * FROM {temp_table_name} where date >= {start_date_unix} AND date <= {end_date_unix}"  # noqa: E501
            )
        )
        db.commit()
        print("Moved data to partition table: ", partition_name)


def create_partition_table_by_params(start_date_unix: int, end_date_unix: int):
    if not start_date_unix or not end_date_unix:
        raise ValueError("Both start_date_unix and end_date_unix must be provided")

    start_date = datetime.fromtimestamp(start_date_unix).replace(hour=0, minute=0, second=0, day=1)
    end_date = datetime.fromtimestamp(end_date_unix)
    time_range = relativedelta(end_date, start_date)
    months_difference = time_range.years * 12 + time_range.months

    if time_range.days > 0:
        months_difference += 1

    if months_difference < 1:
        raise ValueError("The difference between start_date and end_date must be at least 1 month")

    start_date_unix = int(start_date.timestamp())

    for i in range(0, months_difference):  # noqa: B007
        partition_name = get_partition_name_from_unix(start_date_unix)
        end_date = start_date.replace(
            day=calendar.monthrange(start_date.year, start_date.month)[1],
            hour=23,
            minute=59,
            second=59,
            microsecond=999999,
        )
        end_date_unix = int(end_date.timestamp())

        try:
            create_partition_table(partition_name, start_date_unix, end_date_unix)

        except IntegrityError as e:
            if "updated partition constraint for default partition" in str(e):
                print(
                    f"IntegrityError detected: {e}.\n\nHandling overlapping data for partition {partition_name}.\n"  # noqa: E501
                )

                create_temp_table()
                move_data_to_temp_table(start_date_unix, end_date_unix)
                delete_data_from_default_partition(start_date_unix, end_date_unix)
                create_partition_table(partition_name, start_date_unix, end_date_unix)
                migrate_data_to_partition_table(partition_name, start_date_unix, end_date_unix)
                delete_temp_table()

            else:
                raise e

        except Exception as e:
            raise e

        start_date_unix = end_date_unix + 1
        start_date = datetime.fromtimestamp(start_date_unix)


if __name__ == "__main__":
    start_date_ = int(datetime(2018, 1, 1, tzinfo=UTC).timestamp())
    end_date_ = int(datetime(2030, 12, 31, tzinfo=UTC).timestamp())

    create_partition_table_by_params(start_date_, end_date_)
