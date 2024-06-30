from flask import Blueprint, render_template, redirect, url_for, request, jsonify, abort, flash, send_file
from app.models import InlinePolicy, UserAttachedPolicy, UserInlinePolicy, db, Account, Role, TrustedUser, User, AttachedPolicy
from collections import defaultdict
import json
import asyncio
from app.aws_analyzer import AWSRoleAnalyzer
import boto3
import pandas as pd
import os
import logging

main_bp = Blueprint('main', __name__)

sts_client = boto3.client('sts')

def init_routes(app):
    app.register_blueprint(main_bp)

@main_bp.route('/')
def index():
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)

    if search_query:
        accounts = Account.query.filter(Account.account_name.ilike(f'%{search_query}%')).paginate(page=page, per_page=5)
    else:
        accounts = Account.query.paginate(page=page, per_page=10)

    return render_template('main-template.html', accounts=accounts, search_query=search_query)

@main_bp.route('/account/<int:account_id>')
def account_details(account_id):
    account = Account.query.get(account_id)
    if not account:
        abort(404)
 
    roles = Role.query.filter_by(account_id=account.id).all()
    trusted_users = fetch_trusted_users(account.id)
    attached_policies = fetch_attached_policies(account.id)
    users = User.query.filter_by(account_id=account.id).all()
 
    return render_template('account-details.html', account=account, roles=roles, trusted_users=trusted_users, attached_policies=attached_policies, users=users)
 

@main_bp.route('/role/<int:account_id>/<string:role_name>')
def role_policies(account_id, role_name):
    role = Role.query.filter_by(account_id=account_id, role_name=role_name).first()
    if not role:
        abort(404)

    attached_policies = AttachedPolicy.query.filter_by(role_id=role.id).all()
    inline_policies = InlinePolicy.query.filter_by(role_id=role.id).all()

    return jsonify({
        'role_name': role.role_name,
        'attached_policies': [{'name': policy.name, 'document': json.loads(policy.document)} for policy in attached_policies],
        'inline_policies': [{'name': policy.name, 'document': json.loads(policy.document)} for policy in inline_policies]
    })

@main_bp.route('/user/<int:account_id>/<string:user_name>')
def user_policies(account_id, user_name):
    user = User.query.filter_by(account_id=account_id, user_name=user_name).first()
    if not user:
        abort(404)

    attached_policies = UserAttachedPolicy.query.filter_by(user_id=user.id).all()
    inline_policies = UserInlinePolicy.query.filter_by(user_id=user.id).all()

    return jsonify({
        'user_name': user.user_name,
        'attached_policies': [{'name': policy.name, 'document': json.loads(policy.document)} for policy in attached_policies],
        'inline_policies': [{'name': policy.name, 'document': json.loads(policy.document)} for policy in inline_policies]
    })

def fetch_trusted_users(account_id):
    trusted_users = defaultdict(list)
    trusted_users_query = db.session.query(TrustedUser, Role).join(Role).filter(Role.account_id == account_id).all()
    for trusted_user, role in trusted_users_query:
        trusted_users[role.role_name].append({
            'user_arn': trusted_user.user_arn,
            'account': role.account.account_name,
            'role': role.role_name
        })
    return trusted_users

def fetch_attached_policies(account_id):
    attached_policies = defaultdict(list)
    attached_policies_query = db.session.query(AttachedPolicy, Role).join(Role).filter(Role.account_id == account_id).all()
    for attached_policy, role in attached_policies_query:
        attached_policies[role.role_name].append({
            'name': attached_policy.name,
            'document': json.dumps(json.loads(attached_policy.document), indent=4)
        })
    return attached_policies

@main_bp.route('/trusted-users')
def trusted_users():
    try:
        trusted_users = TrustedUser.query.all()
        trusted_users_dict = defaultdict(list)
        for trusted_user in trusted_users:
            account = Account.query.get(trusted_user.account_id)
            role = Role.query.get(trusted_user.role_id)
            trusted_users_dict[trusted_user.user_arn].append({
                'account': account.account_name,
                'role': role.role_name
            })
        return render_template('trusted-users.html', trusted_users=trusted_users_dict)
    except Exception as e:
        flash(f"An error occurred while fetching trusted users: {str(e)}", "danger")
        return redirect(url_for('main.index'))

@main_bp.route('/user-details/<path:user_arn>')
def user_details(user_arn):
    try:
        trusted_users = TrustedUser.query.filter_by(user_arn=user_arn).all()
        if not trusted_users:
            flash(f"No trusted users found for ARN: {user_arn}", "warning")
            return render_template('user-not-found.html', user_arn=user_arn), 404

        user_details = fetch_user_details(trusted_users)
        return render_template('user-details.html', user_arn=user_arn, user_details=user_details)
    except Exception as e:
        logging.error(f"Error in user_details route: {str(e)}", exc_info=True)
        flash(f"An error occurred while fetching user details: {str(e)}", "danger")
        return redirect(url_for('main.index'))

def fetch_user_details(trusted_users):
    user_details = defaultdict(dict)
    for trusted_user in trusted_users:
        account = Account.query.get(trusted_user.account_id)
        role = Role.query.get(trusted_user.role_id)

        attached_policies = [
            {'name': policy.name, 'document': json.dumps(json.loads(policy.document), indent=4)}
            for policy in role.attached_policies
        ]

        inline_policies = [
            {'name': policy.name, 'document': json.dumps(json.loads(policy.document), indent=4)}
            for policy in InlinePolicy.query.filter_by(role_id=role.id).all()
        ]

        role_policies = {}
        if attached_policies:
            role_policies['attached_policies'] = attached_policies
        if inline_policies:
            role_policies['inline_policies'] = inline_policies

        if role_policies:
            user_details[f"{account.account_name} - {account.id}"][role.role_name] = role_policies

    return user_details

@main_bp.route('/update-data')
def update_data():
    try:
        accounts = Account.query.all()
        analyzer = AWSRoleAnalyzer(sts_client, db.session)

        for account in accounts:
            try:
                asyncio.run(analyze_account_async(analyzer, account))
                flash(f"Data updated successfully for account '{account.account_name}'", "success")
            except Exception as e:
                flash(f"Error updating data for account '{account.account_name}': {str(e)}", "danger")

    except Exception as e:
        flash(f"An error occurred while updating data: {str(e)}", "danger")

    return redirect(url_for('main.index'))

async def analyze_account_async(analyzer, account):
    await analyzer.analyze_account(account)

@main_bp.route('/add_account', methods=['GET', 'POST'])
def add_account():
    if request.method == 'POST':
        account_id = request.form['account_id']
        account_name = request.form['account_name']
        role_arn = request.form['role_arn']
        roles_to_analyze = request.form['roles_to_analyze'].split(',')

        if not account_id or not account_name or not role_arn:
            flash('Error: Account ID, Account Name, and Role ARN are required', 'error')
            return redirect(url_for('main.add_account'))

        if Account.query.filter_by(id=account_id).first():
            flash('Error: Account already exists', 'error')
            return redirect(url_for('main.add_account'))

        new_account = Account(id=account_id, account_name=account_name, role_arn=role_arn, roles_to_analyze=roles_to_analyze)
        db.session.add(new_account)
        db.session.commit()

        asyncio.run(sync_aws_data_async(new_account))
        flash('Account added successfully', 'success')
        return redirect(url_for('main.manage_accounts'))

    return render_template('add-account.html')

@main_bp.route('/manage_accounts', methods=['GET', 'POST'])
def manage_accounts():
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    if search_query:
        accounts = Account.query.filter(Account.account_name.ilike(f'%{search_query}%')).paginate(page=page, per_page=10)
    else:
        accounts = Account.query.paginate(page=page, per_page=10)
    return render_template('manage-accounts.html', accounts=accounts, search_query=search_query)

async def sync_aws_data_async(account):
    analyzer = AWSRoleAnalyzer(sts_client, db.session)
    await analyzer.analyze_account(account)

@main_bp.route('/edit_account/<int:account_id>', methods=['GET', 'POST'])
def edit_account(account_id):
    account = Account.query.get(account_id)
    if request.method == 'POST':
        try:
            account.account_name = request.form['account_name']
            account.role_arn = request.form['role_arn']
            account.roles_to_analyze = request.form['roles_to_analyze'].split(',')
            db.session.commit()
            asyncio.run(sync_aws_data_async(account))
            flash("Account updated successfully", "success")
        except Exception as e:
            flash(f"An error occurred while updating the account: {str(e)}", "danger")
        return redirect(url_for('main.manage_accounts'))
    return render_template('edit-account.html', account=account)

@main_bp.route('/delete_account/<int:account_id>', methods=['POST'])
def delete_account(account_id):
    try:
        account = Account.query.get(account_id)
        Role.query.filter_by(account_id=account.id).delete()
        User.query.filter_by(account_id=account.id).delete()
        TrustedUser.query.filter_by(account_id=account.id).delete()
        db.session.delete(account)
        db.session.commit()
        flash("Account deleted successfully", "success")
    except Exception as e:
        flash(f"An error occurred while deleting the account: {str(e)}", "danger")
    return redirect(url_for('main.manage_accounts'))

@main_bp.route('/accounts/add-role', methods=['POST'])
def add_role():
    try:
        role_name = request.form['role_name']
        account_id = request.form['account_id']
        account = Account.query.get(account_id)
        if account:
            if role_name not in account.roles_to_analyze:
                account.roles_to_analyze.append(role_name)
                db.session.commit()
                asyncio.run(sync_aws_data_async(account))
        flash("Role added successfully", "success")
    except Exception as e:
        flash(f"An error occurred while adding the role: {str(e)}", "danger")
    return jsonify(success=True)

@main_bp.route('/accounts/remove-role', methods=['POST'])
def remove_role():
    try:
        role_name = request.form['role_name']
        account_id = request.form['account_id']
        account = Account.query.get(account_id)
        if account:
            if role_name in account.roles_to_analyze:
                account.roles_to_analyze.remove(role_name)
                db.session.commit()

                analyzer = AWSRoleAnalyzer(sts_client, db.session)
                asyncio.run(analyzer.remove_role(account.id, role_name))

        flash("Role removed successfully", "success")
    except Exception as e:
        flash(f"An error occurred while removing the role: {str(e)}", "danger")
    return jsonify(success=True)

@main_bp.route('/export', methods=['GET'])
def export_to_excel():
    try:
        accounts_data = []
        accounts = Account.query.all()
        for account in accounts:
            roles = Role.query.filter_by(account_id=account.id).all()
            for role in roles:
                attached_policies = AttachedPolicy.query.filter_by(role_id=role.id).all()
                inline_policies = InlinePolicy.query.filter_by(role_id=role.id).all()
                trusted_users = TrustedUser.query.filter_by(role_id=role.id).all()
                inline_policies_str = ', '.join([policy.name for policy in inline_policies])
                attached_policies_str = ', '.join([policy.name for policy in attached_policies])
                if inline_policies_str:
                    policy_str = attached_policies_str + ', ' + inline_policies_str
                else:
                    policy_str = attached_policies_str
                trusted_users_str = '\n'.join([user.user_arn for user in trusted_users])
                roles_data = {
                    'Account_No': account.id,
                    'Account Name': account.account_name,
                    'Role Name': role.role_name,
                    'Role Attached Policy': policy_str,
                    'Users Attached Role': trusted_users_str
                }
                accounts_data.append(roles_data)

        df = pd.DataFrame(accounts_data)
        file_path = 'exported_data.xlsx'
        df.to_excel(file_path, index=False)

        response = send_file(file_path, as_attachment=True)
        response.call_on_close(lambda: os.remove(file_path))

        return response
    except Exception as e:
        flash(f"An error occurred while exporting data: {str(e)}", "danger")
        return redirect(url_for('main.index'))
