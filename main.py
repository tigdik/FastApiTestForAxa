import re
import sqlite3
from enum import Enum
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, field_validator, conint
from fastapi.testclient import TestClient

###############################################################################
# 1. Pydantic Models
###############################################################################
class AccountStatus(Enum):
    ACTIVE = "Active"
    DISABLED = "Disabled"
    DELETED = "Deleted"
    IN_PROGRESS = "In progress"


class User(BaseModel):
    name: str
    surname: str
    age: conint(ge=18, le=120)  # Age must be between 18 and 120

    @field_validator("name")
    def validate_name_letters_only(cls, value):
        if not re.match(r"^[A-Za-z]+$", value):
            raise ValueError("User.name must contain letters only")
        return value

    @field_validator("surname")
    def validate_surname_letters_only(cls, value):
        if not re.match(r"^[A-Za-z]+$", value):
            raise ValueError("User.surname must contain letters only")
        return value


class Login(BaseModel):
    username: str
    password: str

    @field_validator("username")
    def validate_username_alphanumeric(cls, value):
        if not re.match(r"^[A-Za-z0-9]+$", value):
            raise ValueError("username must contain only letters or digits")
        return value

    @field_validator("password")
    def validate_password_strength(cls, value):
        # Min length 10
        if len(value) < 10:
            raise ValueError("password must be at least 10 characters long")
        # At least one capital letter
        if not re.search(r"[A-Z]", value):
            raise ValueError("password must contain at least one capital letter")
        # At least one digit
        if not re.search(r"\d", value):
            raise ValueError("password must contain at least one number")
        return value



class AccountCreate(BaseModel):
    """
    Input model for creating an account:
    No 'status' field because we default to IN_PROGRESS in the endpoint.
    """
    user: User
    login: Login


###############################################################################
# 2. Lifespan: Start/Stop Database connection
###############################################################################

conn: Optional[sqlite3.Connection] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Create an in-memory SQLite database on startup.
    Close the connection on shutdown.
    """
    global conn
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            surname TEXT NOT NULL,
            age INTEGER NOT NULL,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            status TEXT NOT NULL
        );
    """)
    conn.commit()

    try:
        yield
    finally:
        conn.close()


###############################################################################
# 3. Initialize FastAPI
###############################################################################

app = FastAPI(
    title="Axa Test Restful microservice",
    lifespan=lifespan  # attach the lifespan context manager
)


###############################################################################
# 4. Endpoints
###############################################################################

@app.post("/register_account")
def register_account(account_data: AccountCreate):

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO accounts (name, surname, age, username, password, status)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (
                account_data.user.name,
                account_data.user.surname,
                account_data.user.age,
                account_data.login.username,
                account_data.login.password,
                AccountStatus.IN_PROGRESS.value,
            )
        )
        conn.commit()
    except sqlite3.IntegrityError as e:
        # Example: UNIQUE constraint on username
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not create account: {str(e)}",
        )

    return {"message": "Thank you for registering!"}


@app.post("/login")
def login(credentials: Login):
    """
    POST /login
    1) Look up user by (username, password).
    2) If found => set status = ACTIVE => "Hello, [User.name]!"
    3) If not found => 404 => "User [username] Not Found"
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, name, status
        FROM accounts
        WHERE username = ? AND password = ?;
        """,
        (credentials.username, credentials.password)
    )
    row = cursor.fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {credentials.username} Not Found",
        )

    account_id, user_name, current_status = row
    if current_status != AccountStatus.ACTIVE.value:
    # Update status to ACTIVE
        cursor.execute(
            """
            UPDATE accounts
            SET status = ?
            WHERE id = ?;
            """,
            (AccountStatus.ACTIVE.value, account_id)
        )
    conn.commit()

    return {"message": f"Hello, {user_name}!"}


###############################################################################
# 5. Unit Tests
###############################################################################

client = TestClient(app)

def test_register_and_login():
    with TestClient(app) as client:
        payload = {
            "user": {"name": "Alice", "surname": "Smith", "age": 25},
            "login": {"username": "Alice123", "password": "BlaBla1234"}
        }
        resp = client.post("/register_account", json=payload)
        assert resp.status_code == 200
        assert resp.json()["message"] == "Thank you for registering!"

        login_payload = {
            "username": "Alice123",
            "password": "BlaBla1234"
        }
        resp2 = client.post("/login", json=login_payload)
        assert resp2.status_code == 200
        assert resp2.json()["message"] == "Hello, Alice!"



def test_register_validation_fail():
    with TestClient(app) as client:
        """
        Test a few validation failures: 
        - age < 18
        - invalid characters in name
        - password too short
        """
        invalid_payload = {
            "user": {"name": "Alice!", "surname": "Smith", "age": 17},
            "login": {"username": "User123", "password": "Short1"}
        }
        resp = client.post("/register_account", json=invalid_payload)
        assert resp.status_code == 422, resp.text


def test_login_user_not_found():
    with TestClient(app) as client:
        """
        If user doesn't exist or password is wrong => 404
        """
        login_payload = {
            "username": "UnknownUser",
            "password": "Whatever123"
        }
        resp = client.post("/login", json=login_payload)
        assert resp.status_code == 404, resp.text
        assert "Not Found" in resp.json()["detail"]
