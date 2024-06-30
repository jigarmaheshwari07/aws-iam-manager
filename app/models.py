from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Account(db.Model):
    id = db.Column(db.String(12), primary_key=True)
    account_name = db.Column(db.String(100), nullable=False)
    role_arn = db.Column(db.String(255), nullable=False)
    roles_to_analyze = db.Column(db.JSON, nullable=False, default=[])
    roles = db.relationship('Role', backref='account', lazy=True)
    users = db.relationship('User', backref='account', lazy=True)

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(100), nullable=False)
    trust_policy = db.Column(db.Text, nullable=False)
    permissions_summary = db.Column(db.Text, nullable=False)
    account_id = db.Column(db.String(12), db.ForeignKey('account.id'), nullable=False)
    attached_policies = db.relationship('AttachedPolicy', backref='role', lazy=True)
    inline_policies = db.relationship('InlinePolicy', backref='role', lazy=True)
    trusted_users = db.relationship('TrustedUser', backref='role', lazy=True)

class AttachedPolicy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    document = db.Column(db.Text, nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)

class InlinePolicy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    document = db.Column(db.Text, nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)



class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(100), nullable=False)
    account_id = db.Column(db.String(12), db.ForeignKey('account.id'), nullable=False)
    attached_policies = db.relationship('UserAttachedPolicy', backref='user', lazy=True)
    inline_policies = db.relationship('UserInlinePolicy', backref='user', lazy=True)


class UserAttachedPolicy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    document = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class UserInlinePolicy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    document = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class TrustedUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_arn = db.Column(db.String(255), nullable=False)
    account_id = db.Column(db.String(12), db.ForeignKey('account.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
