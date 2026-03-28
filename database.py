from snowflake.snowpark.context import get_active_session

DB   = "SKYBOOK_DB"
SCH  = "BOOKING"
PASS = f"{DB}.{SCH}.PASSENGERS"
AIR  = f"{DB}.{SCH}.AIRLINES"
FLT  = f"{DB}.{SCH}.FLIGHTS"
BKG  = f"{DB}.{SCH}.BOOKINGS"


def get_session():
    return get_active_session()


# ── READ ──────────────────────────────────────────────────────
def get_all_bookings():
    session = get_session()
    df = session.sql(f"""
        SELECT
            b.ID          AS id,
            b.REF         AS ref,
            p.NAME        AS pname,
            p.EMAIL       AS email,
            p.PHONE       AS phone,
            f.FLIGHT_NO   AS flight,
            a.NAME        AS airline,
            f.ORIGIN      AS origin,
            f.DESTINATION AS destination,
            f.TRAVEL_DATE AS travel_date,
            f."CLASS"  AS cls,
            b.PRICE       AS price,
            b.STATUS      AS status
        FROM {BKG} b
        JOIN {PASS} p ON p.ID = b.PASSENGER_ID
        JOIN {FLT}  f ON f.ID = b.FLIGHT_ID
        JOIN {AIR}  a ON a.ID = f.AIRLINE_ID
        ORDER BY b.ID DESC
    """).to_pandas()
    df.columns = [c.lower() for c in df.columns]
    result = []
    for r in df.to_dict("records"):
        r["name"] = r.pop("pname")
        r["from"] = r.pop("origin")
        r["to"]   = r.pop("destination")
        r["date"] = str(r.pop("travel_date"))[:10]
        result.append(r)
    return result


def get_airlines():
    session = get_session()
    df = session.sql(f"SELECT ID AS id, NAME AS name FROM {AIR} ORDER BY NAME").to_pandas()
    df.columns = [c.lower() for c in df.columns]
    return df.to_dict("records")


# ── CREATE ────────────────────────────────────────────────────
def add_booking(name, email, phone, flight_no, airline_name,
                origin, destination, travel_date, cls, price, status):
    session = get_session()

    existing = session.sql(f"SELECT ID FROM {PASS} WHERE EMAIL='{email}'").to_pandas()
    if not existing.empty:
        passenger_id = int(existing.iloc[0]["ID"])
        session.sql(f"UPDATE {PASS} SET NAME='{name}', PHONE='{phone}' WHERE ID={passenger_id}").collect()
    else:
        session.sql(f"INSERT INTO {PASS} (NAME,EMAIL,PHONE) VALUES ('{name}','{email}','{phone}')").collect()
        passenger_id = int(session.sql(f"SELECT MAX(ID) AS mid FROM {PASS}").to_pandas().iloc[0]["MID"])

    air_row = session.sql(f"SELECT ID FROM {AIR} WHERE NAME='{airline_name}'").to_pandas()
    if not air_row.empty:
        airline_id = int(air_row.iloc[0]["ID"])
    else:
        session.sql(f"INSERT INTO {AIR} (NAME) VALUES ('{airline_name}')").collect()
        airline_id = int(session.sql(f"SELECT MAX(ID) AS mid FROM {AIR}").to_pandas().iloc[0]["MID"])

    session.sql(f"""
        INSERT INTO {FLT} (AIRLINE_ID,FLIGHT_NO,ORIGIN,DESTINATION,TRAVEL_DATE,CLASS)
        VALUES ({airline_id},'{flight_no}','{origin}','{destination}','{travel_date}','{cls}')
    """).collect()
    flight_id = int(session.sql(f"SELECT MAX(ID) AS mid FROM {FLT}").to_pandas().iloc[0]["MID"])

    cnt = int(session.sql(f"SELECT COUNT(*) AS cnt FROM {BKG}").to_pandas().iloc[0]["CNT"])
    ref = f"SB-{10021 + cnt}"

    session.sql(f"""
        INSERT INTO {BKG} (REF,PASSENGER_ID,FLIGHT_ID,PRICE,STATUS)
        VALUES ('{ref}',{passenger_id},{flight_id},{price},'{status}')
    """).collect()


# ── UPDATE ────────────────────────────────────────────────────
def update_booking(booking_id, name, email, phone, flight_no, airline_name,
                   origin, destination, travel_date, cls, price, status):
    session = get_session()

    row = session.sql(f"SELECT PASSENGER_ID, FLIGHT_ID FROM {BKG} WHERE ID={booking_id}").to_pandas()
    if row.empty:
        return

    passenger_id = int(row.iloc[0]["PASSENGER_ID"])
    flight_id    = int(row.iloc[0]["FLIGHT_ID"])

    session.sql(f"UPDATE {PASS} SET NAME='{name}',EMAIL='{email}',PHONE='{phone}' WHERE ID={passenger_id}").collect()

    air_row = session.sql(f"SELECT ID FROM {AIR} WHERE NAME='{airline_name}'").to_pandas()
    if not air_row.empty:
        airline_id = int(air_row.iloc[0]["ID"])
    else:
        session.sql(f"INSERT INTO {AIR} (NAME) VALUES ('{airline_name}')").collect()
        airline_id = int(session.sql(f"SELECT MAX(ID) AS mid FROM {AIR}").to_pandas().iloc[0]["MID"])

    session.sql(f"""
        UPDATE {FLT}
        SET AIRLINE_ID={airline_id}, FLIGHT_NO='{flight_no}', ORIGIN='{origin}',
            DESTINATION='{destination}', TRAVEL_DATE='{travel_date}', CLASS='{cls}'
        WHERE ID={flight_id}
    """).collect()

    session.sql(f"UPDATE {BKG} SET PRICE={price}, STATUS='{status}' WHERE ID={booking_id}").collect()


def update_booking_status(ref: str, new_status: str):
    session = get_session()
    session.sql(f"UPDATE {BKG} SET STATUS='{new_status}' WHERE REF='{ref}'").collect()


# ── DELETE ────────────────────────────────────────────────────
def delete_booking(booking_id: int = None, ref: str = None):
    session = get_session()
    if booking_id:
        session.sql(f"DELETE FROM {BKG} WHERE ID={booking_id}").collect()
    elif ref:
        session.sql(f"DELETE FROM {BKG} WHERE REF='{ref}'").collect()
