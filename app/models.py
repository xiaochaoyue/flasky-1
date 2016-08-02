# coding=utf-8
from . import db  # 在当前目录下导入db
from . import login_manager

from werkzeug.security import generate_password_hash, check_password_hash  # 加入密码散列
from flask_login import UserMixin, AnonymousUserMixin  # 支持用户登陆,检查用户权限
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app


class Permission(object):  # 程序权限常量：关注、评论、写文章、修改评论、管理网站
    Follow = 0x01
    COMMENT = 0x02
    WRITE_ARTICLES = 0x04
    MODERATE_COMMENTS = 0x08
    ADMINISTER = 0x80


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)  # 权限
    users = db.relationship('User', backref='role', lazy='dynamic')  # P49 构造关系，返回User模型中，与角色关联的用户组成的列表

    def __repr__(self):
        return '<Role {}'.format(self.name)  # 返回一个可读性的字符串表示模型，测试时候使用

    @staticmethod
    def insert_roles():
        roles = {
            'User': (Permission.Follow |
                     Permission.COMMENT |
                     Permission.WRITE_ARTICLES, True),
            'Moderator': (Permission.Follow |
                          Permission.COMMENT |
                          Permission.WRITE_ARTICLES |
                          Permission.MODERATE_COMMENTS, False),
            'Administrator': (0xff, False)
        }  # 角色字典，|按位或，将权限位值组合起来
        for r in roles:
            role = Role.query.filter_by(name=r).first()  # 数据库查找有无角色字典里的用户行
            if role is None:
                role = Role(name=r)  # 新建一行
            role.permissions = roles[r][0]  #
            role.default = roles[r][1]  # 默认角色，这里为User
            db.session.add(role)  # 添加到数据库会话
        db.session.commit()  # 提交


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    confirmed = db.Column(db.Boolean, default=False)

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)  # 调用基类的构造函数
        if self.role is None:
            if self.email == current_app.config['FLASKY_ADMIN']:
                self.role == Role.query.filter_by(permissions=0xff).first()  # 定义管理员
            if self.role is None:
                self.none = Role.query.filter_by(default=True).first()  # 定义默认用户

    def __repr__(self):
        return '<User {}'.format(self.name)

    @property  # 只写属性.
    def password(self):  # 读取password会报错
        raise AttributeError('password is not a readable attribute')

    @password.setter  # 设定值
    def password(self, password):
        self.password_hash = generate_password_hash(password)  # 调用生成hash赋值给password_hash字段

    def verify_password(self, password):  # 与存储在User模型中的密码散列值对比
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)  # 生成token,有效期一个小时
        return s.dumps({'confirm': self.id})  # 为指定的数据生成加密签名，令牌字符串

    def confirm(self, token):  # 检验token
        s = Serializer(current_app.config['SECRET_KEY'])  # 生成token
        try:
            data = s.loads(token)  # 解码token，
        except:  # 捕获抛出的所有异常
            return False
        if data.get('confirm') != self.id:  # 检验token中的ID与current_user保存的已登录用户匹配
            return False
        self.confirmed = True  # 检验通过，设为True,self表示一行
        db.session.add(self)  # 添加到数据库会话
        return True

    def can(self, permissions):  # 如果角色包含请求的所有权限位，返回True
        return self.role is not None and \
               (self.role.permissions & permissions) == permissions

    def is_administrator(self):
        return self.can(Permission.ADMINISTER)



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
