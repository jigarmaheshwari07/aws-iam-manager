# Your Flask App

## Description
This project is a Flask application that integrates with AWS to manage and analyze IAM roles, users, and policies.

## Setup

1. **Clone the repository**
    ```sh
    git clone https://github.com/Paresh-Maheshwari/aws-iam-manager.git
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

To run the CLI commands, make sure you are in the root directory of your Flask application.

- **Update AWS Data**
    ```sh
    flask update-aws-data
    ```

This command will update the data from AWS, including IAM roles, users, and policies.

- **Sync Account**
    ```sh
    flask sync-account --account_id <ACCOUNT_ID>
    ```

Replace `<ACCOUNT_ID>` with the ID of the AWS account you want to sync. This command will sync the specified AWS account with your Flask application.

Remember to replace `<ACCOUNT_ID>` with the actual ID of the AWS account you want to sync.


## License
This project is licensed under the MIT License.
