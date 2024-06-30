import boto3
import json
from collections import defaultdict
from app.models import UserAttachedPolicy, UserInlinePolicy, db, Account, Role, AttachedPolicy, InlinePolicy, User, TrustedUser
from sqlalchemy.orm import scoped_session, sessionmaker
from flask import current_app
import asyncio
import logging

class AWSRoleAnalyzer:
    def __init__(self, sts_client, session):
        self.sts_client = sts_client
        self.session = session
        self.results = {}
        self.trusted_users = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        self.logger = logging.getLogger(__name__)

    def assume_role(self, role_arn):
        try:
            response = self.sts_client.assume_role(
                RoleArn=role_arn,
                RoleSessionName='AssumeRoleSession'
            )
            credentials = response['Credentials']
            return boto3.client(
                'iam',
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken']
            )
        except Exception as e:
            self.logger.error(f"Error assuming role {role_arn}: {e}")
            return None

    def get_role_info(self, iam_client, role_name):
        try:
            role = iam_client.get_role(RoleName=role_name)
            attached_policies = iam_client.list_attached_role_policies(RoleName=role_name)
            inline_policies = iam_client.list_role_policies(RoleName=role_name)
            return {
                'role': role,
                'attached_policies': attached_policies,
                'inline_policies': inline_policies
            }
        except iam_client.exceptions.NoSuchEntityException:
            self.logger.warning(f"Role '{role_name}' not found.")
            return None
        except Exception as e:
            self.logger.error(f"Error getting role info for {role_name}: {e}")
            return None

    def get_policy_document(self, iam_client, policy_arn):
        try:
            policy = iam_client.get_policy(PolicyArn=policy_arn)
            policy_version = iam_client.get_policy_version(
                PolicyArn=policy_arn,
                VersionId=policy['Policy']['DefaultVersionId']
            )
            return policy_version['PolicyVersion']['Document']
        except Exception as e:
            self.logger.error(f"Error fetching policy document for {policy_arn}: {e}")
            return None

    def extract_account_number(self, arn):
        parts = arn.split(':')
        return parts[4] if len(parts) >= 5 else None

    def extract_trusted_entities(self, trust_policy):
        trusted_entities = []
        for statement in trust_policy.get('Statement', []):
            principal = statement.get('Principal', {})
            if 'AWS' in principal:
                if isinstance(principal['AWS'], list):
                    trusted_entities.extend(principal['AWS'])
                else:
                    trusted_entities.append(principal['AWS'])
        return trusted_entities

    def summarize_permissions(self, policy_document, permissions_summary):
        for statement in policy_document.get('Statement', []):
            effect = statement.get('Effect', 'Allow')
            actions = statement.get('Action', [])
            if isinstance(actions, str):
                actions = [actions]
            for action in actions:
                permissions_summary[effect].add(action)

    async def analyze_account(self, account):
        iam_client = self.assume_role(account.role_arn)
        if not iam_client:
            return

        account_name = account.account_name
        account_number = self.extract_account_number(account.role_arn)
        self.results[account_name] = {}

        account_db = self.session.get(Account, account_number)
        if not account_db:
            account_db = Account(id=account_number, account_name=account_name)
            self.session.add(account_db)
        else:
            account_db.account_name = account_name

        existing_roles = set(role.role_name for role in Role.query.filter_by(account_id=account_db.id).all())

        tasks = []
        for role_name in account.roles_to_analyze:
            tasks.append(asyncio.create_task(self.analyze_role(iam_client, role_name, account_db)))
            if role_name in existing_roles:
                existing_roles.remove(role_name)

        await asyncio.gather(*tasks)

        for role_name in existing_roles:
            await self.remove_role(account_db.id, role_name)

        await self.get_users_and_policies(account)

        self.session.commit()

    async def remove_role(self, account_id, role_name):
        role = Role.query.filter_by(account_id=account_id, role_name=role_name).first()
        if role:
            AttachedPolicy.query.filter_by(role_id=role.id).delete()
            InlinePolicy.query.filter_by(role_id=role.id).delete()
            TrustedUser.query.filter_by(role_id=role.id).delete()
            self.session.delete(role)
            self.logger.info(f"Removed role '{role_name}' and its associated data from account {account_id}")

    async def analyze_role(self, iam_client, role_name, account_db):
        role_info = self.get_role_info(iam_client, role_name)
        if role_info:
            trust_policy = role_info['role']['Role']['AssumeRolePolicyDocument']
            trusted_entities = self.extract_trusted_entities(trust_policy)

            permissions_summary = defaultdict(set)
            for policy in role_info['attached_policies']['AttachedPolicies']:
                policy_document = self.get_policy_document(iam_client, policy['PolicyArn'])
                if policy_document:
                    self.summarize_permissions(policy_document, permissions_summary)

            for policy_name in role_info['inline_policies']['PolicyNames']:
                policy_document = iam_client.get_role_policy(RoleName=role_name, PolicyName=policy_name)
                self.summarize_permissions(policy_document['PolicyDocument'], permissions_summary)

            role = Role.query.filter_by(role_name=role_name, account_id=account_db.id).first()
            if not role:
                role = Role(
                    role_name=role_name,
                    trust_policy=json.dumps(trust_policy),
                    permissions_summary=json.dumps({k: list(v) for k, v in permissions_summary.items()}),
                    account_id=account_db.id
                )
                self.session.add(role)
                self.session.flush()

            for policy in role_info['attached_policies']['AttachedPolicies']:
                policy_document = self.get_policy_document(iam_client, policy['PolicyArn'])
                if policy_document:
                    attached_policy = AttachedPolicy.query.filter_by(name=policy['PolicyName'], role_id=role.id).first()
                    if not attached_policy:
                        attached_policy = AttachedPolicy(
                            name=policy['PolicyName'],
                            document=json.dumps(policy_document),
                            role_id=role.id
                        )
                        self.session.add(attached_policy)

            for policy_name in role_info['inline_policies']['PolicyNames']:
                policy_document = iam_client.get_role_policy(RoleName=role_name, PolicyName=policy_name)
                inline_policy = InlinePolicy.query.filter_by(name=policy_name, role_id=role.id).first()
                if not inline_policy:
                    inline_policy = InlinePolicy(
                        name=policy_name,
                        document=json.dumps(policy_document['PolicyDocument']) if 'PolicyDocument' in policy_document else None,
                        role_id=role.id
                    )
                    self.session.add(inline_policy)

            for entity in trusted_entities:
                trusted_user = TrustedUser.query.filter_by(user_arn=entity, account_id=account_db.id, role_id=role.id).first()
                if not trusted_user:
                    trusted_user = TrustedUser(
                        user_arn=entity,
                        account_id=account_db.id,
                        role_id=role.id
                    )
                    self.session.add(trusted_user)

    async def get_users_and_policies(self, account):
        iam_client = self.assume_role(account.role_arn)
        users = iam_client.list_users()['Users']

        tasks = []
        for user in users:
            tasks.append(asyncio.create_task(self.process_user(iam_client, user, account)))

        await asyncio.gather(*tasks)

    async def process_user(self, iam_client, user, account):
        user_name = user['UserName']
        attached_policies = iam_client.list_attached_user_policies(UserName=user_name)
        inline_policies = iam_client.list_user_policies(UserName=user_name)

        attached_policy_names = [policy['PolicyName'] for policy in attached_policies['AttachedPolicies']]
        attached_policy_arns = [policy['PolicyArn'] for policy in attached_policies['AttachedPolicies']]
        inline_policy_names = [policy for policy in inline_policies['PolicyNames']]

        user_record = User.query.filter_by(user_name=user_name, account_id=account.id).first()
        if not user_record:
            user_record = User(
                user_name=user_name,
                account_id=account.id
            )
            self.session.add(user_record)
            self.session.flush()

        for policy_name, policy_arn in zip(attached_policy_names, attached_policy_arns):
            policy_document = self.get_policy_document(iam_client, policy_arn)
            if policy_document:
                attached_policy = UserAttachedPolicy.query.filter_by(name=policy_name, user_id=user_record.id).first()
                if not attached_policy:
                    attached_policy = UserAttachedPolicy(
                        name=policy_name,
                        document=json.dumps(policy_document),
                        user_id=user_record.id
                    )
                    self.session.add(attached_policy)
                else:
                    attached_policy.document = json.dumps(policy_document)

        for policy_name in inline_policy_names:
            policy_document = iam_client.get_user_policy(UserName=user_name, PolicyName=policy_name)
            if 'PolicyDocument' in policy_document:
                inline_policy = UserInlinePolicy.query.filter_by(name=policy_name, user_id=user_record.id).first()
                if not inline_policy:
                    inline_policy = UserInlinePolicy(
                        name=policy_name,
                        document=json.dumps(policy_document['PolicyDocument']),
                        user_id=user_record.id
                    )
                    self.session.add(inline_policy)
                else:
                    inline_policy.document = json.dumps(policy_document['PolicyDocument'])

        self.session.commit()
def init_aws_analyzer(app):
    sts_client = boto3.client('sts')

    @app.cli.command("update-aws-data")
    def update_aws_data():
        with app.app_context():
            Session = scoped_session(sessionmaker(bind=db.engine))
            accounts = Account.query.all()
            analyzer = AWSRoleAnalyzer(sts_client, Session())

            async def process_accounts():
                tasks = [asyncio.create_task(analyzer.analyze_account(account)) for account in accounts]
                await asyncio.gather(*tasks)

            asyncio.run(process_accounts())
            print("AWS data update completed.")

    @app.cli.command("sync-account")
    def sync_account(account_id):
        with app.app_context():
            Session = scoped_session(sessionmaker(bind=db.engine))
            account = Account.query.get(account_id)
            if account:
                analyzer = AWSRoleAnalyzer(sts_client, Session())
                asyncio.run(analyzer.analyze_account(account))
                print(f"Account {account.account_name} synced successfully.")
            else:
                print(f"Account with ID {account_id} not found.")