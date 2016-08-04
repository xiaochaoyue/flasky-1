# coding=utf-8
from datetime import datetime
from flask import render_template, session, redirect, \
    url_for, current_app, abort, flash  # 程序上下文，当前激活程序的实例
from flask_login import current_user, login_required

from . import main  # 从这一层的__init__.py导入蓝本实例
from .forms import NameForm, EditProfileForm  # 从这一层的forms.py导入NameForm
from .. import db  # 从上一层的__init__.py导入数据库实例db
from ..models import User  # 从上一层的models.py导入User数据库对象
from ..email import send_email


@main.route('/', methods=['GET', 'POST'])
def index():
    form = NameForm()
    if form.validate_on_submit():  # 如果数据能被所有验证函数接受，validate_on_submit()返回True
        user = User.query.filter_by(username=form.name.data).first()  # 查询数据库中有无表单中输入的名字
        if user is None:
            user = User(username=form.name.data)  # 把前端返回的form里面的name，生成一个User模型的实例（也就是表的一行）
            db.session.add(user)  # 然后添加到数据库的session准备commit
            session['known'] = False  # 然后把flask的session里面的'known'设置为False，表示这个name以前没出现过
            if current_app.config['FLASKY_ADMIN']:  # 判断配置环境里有无收件人
                send_email(current_app.config['FLASKY_ADMIN'], 'New User', 'mail/new_user', user=user)
        else:
            session['known'] = True  # 表示在数据里查询到了，存在的name,代表以前访问过，known设置为True
        session['name'] = form.name.data
        return redirect(url_for('.index'))  # Post重定向Get
    return render_template('index.html',
                           form=form, name=session.get('name'),
                           known=session.get('known', False))


@main.route('/user/<username>')
def user(username):
    """资料显示页面的路由"""
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    return render_template('user.html', user=user)


@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """资料编辑路由"""
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.location.data
        db.session.add(current_user)
        flash('Your profile has been updated.')
        return redirect(url_for('.user'), username=current_user.username)
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)
