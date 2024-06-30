# Your Flask App

## Description
This project is a Flask application that integrates with AWS to manage and analyze IAM roles, users, and policies.

## Setup

1. **Clone the repository**
    ```sh
    git clone https://github.com/your-repo/your-flask-app.git
    cd your-flask-app
    ```

2. **Create and activate a virtual environment**
    ```sh
    python3 -m venv venv
    source venv/bin/activate
    ```

3. **Install the dependencies**
    ```sh
    pip install -r requirements.txt
    ```

4. **Set up the environment variables**
    Create a `.env` file in the root directory and add the following:
    ```plaintext
    DATABASE_URL=sqlite:///aws_roles.db
    SECRET_KEY=supersecretkey
    ```

5. **Run the application**
    ```sh
    flask run
    ```

## Usage

- Visit `http://127.0.0.1:5000/` to access the application.
- Use the CLI commands to update and sync AWS data.

## CLI Commands

- **Update AWS Data**
    ```sh
    flask update-aws-data
    ```

- **Sync Account**
    ```sh
    flask sync-account --account_id <ACCOUNT_ID>
    ```

## License
This project is licensed under the MIT License.
