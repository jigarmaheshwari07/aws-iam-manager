
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import csv
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///aws_roles.db'
db = SQLAlchemy(app)


class Account(db.Model):
    id = db.Column(db.String(12), primary_key=True)
    account_name = db.Column(db.String(100), nullable=False)
    role_arn = db.Column(db.String(255), nullable=False)
    roles_to_analyze = db.Column(db.JSON, nullable=False, default=[])

def update_accounts_from_csv(csv_file_path):
    with app.app_context():
        with open(csv_file_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                account_id = row['id']
                role_arn = f"arn:aws:iam::{account_id}:role/reports"

                # Fix roles_to_analyze list
                roles_to_analyze = ["Aeonx-L1-Role", "Aeonx-L2-Role", "Aeonx-L3-Role", "Aeonx-Sec-Role"]

                # Retrieve the account from the database
                account = Account.query.get(account_id)
                if account:
                    account.account_name = row['account_name']
                    account.role_arn = role_arn
                    account.roles_to_analyze = roles_to_analyze
                else:
                    # Create new account if not found
                    account = Account(
                        id=account_id,
                        account_name=row['account_name'],
                        role_arn=role_arn,
                        roles_to_analyze=roles_to_analyze
                    )
                    db.session.add(account)
        
        db.session.commit()

if __name__ == "__main__":
    csv_file_path = 'output.csv'  # Path to your CSV file
    update_accounts_from_csv(csv_file_path)