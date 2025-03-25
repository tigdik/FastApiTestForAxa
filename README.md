# FastAPI Plain SQL Account Application

This repository contains a simple FastAPI application that uses an in-memory SQLite database via plain SQL (no ORM) to manage account registrations and logins. The application validates input with Pydantic and uses plain SQL statements for database interactions.

## Endpoints and Test Commands

Below are the curl commands to test the endpoints for registration and login.

---

## 1. Register Account

**Endpoint:** `/register_account`  
**Method:** POST  
**Description:** Accepts a JSON payload with user details and login credentials. The account is created with a default status of `IN_PROGRESS`.

### Successful Registration

Register a new account with valid data:

```bash
curl -X POST "http://localhost:8000/register_account" \
  -H "Content-Type: application/json" \
  -d '{
        "user": {
          "name": "Alice",
          "surname": "Smith",
          "age": 25
        },
        "login": {
          "username": "Alice123",
          "password": "SecurePass1"
        }
      }'
```
### Registration Validation Failure
This command tests the input validations. It will fail because:
* name contains an invalid character (!)
* age is below 18
* password is too short
```bash
curl -X POST "http://localhost:8000/register_account" \
  -H "Content-Type: application/json" \
  -d '{
        "user": {
          "name": "Alice!",
          "surname": "Smith",
          "age": 17
        },
        "login": {
          "username": "User123",
          "password": "Short1"
        }
      }'
```

## 2. Login
**Endpoint:** `/login`
**Method:** POST 
**Description:** Accepts a JSON payload with login credentials. If a matching account is found, the account's status is updated to ACTIVE (if it is not already) and the user is greeted. If no account is found, a 404 error is returned.

### Successful Login
Assuming the account was registered successfully, log in with the correct credentials:
```bash
curl -X POST "http://localhost:8000/login" \
  -H "Content-Type: application/json" \
  -d '{
        "username": "Alice123",
        "password": "SecurePass1"
      }'
```

### Login User Not Found
This command tests the scenario when the user credentials are not found in the database:
```bash
curl -X POST "http://localhost:8000/login" \
  -H "Content-Type: application/json" \
  -d '{
        "username": "UnknownUser",
        "password": "AnyPassword1"
      }'
```

## Running the Application

1. **Install Dependencies:**

   Ensure you have Python installed, then run:
```bash
   pip install fastapi uvicorn pydantic
```

2. **Start the Application:**

Run the following command to start the FastAPI server:
```bash
    uvicorn main:app --reload
```
The application will be available at http://localhost:8000.

3. **Test the Endpoints:**

Use the provided curl commands (see above) in your terminal to test the registration and login endpoints.


---

## Notes

* Data Validation:
Input data is validated using Pydantic. Validation errors result in a 422 Unprocessable Entity response along with details about the errors.

* In-Memory Database:
The application uses an in-memory SQLite database. This means that data is not persisted across restarts. Every time the app is restarted, a fresh database is created.

* Password Storage:
For demonstration purposes, passwords are stored in plain text. In a production environment, passwords should always be hashed (using libraries like bcrypt or passlib) before storage.

* Lifespan Event Handling:
The application leverages FastAPI’s lifespan event handler (instead of deprecated on_event) to initialize the database on startup and clean up on shutdown.
