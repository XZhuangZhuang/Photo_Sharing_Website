# -*- encoding=UTF-8 -*-

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

app = Flask(__name__)
# 这条语句可以扩展break或continue在if语句中可以使用
app.jinja_env.add_extension('jinja2.ext.loopcontrols')
app.config.from_pyfile('app.conf')
app.secret_key = 'nowcoder'

# 定义数据库
db = SQLAlchemy(app)

login_manager = LoginManager(app)  # 登陆
login_manager.login_view = '/regloginpage/'  # 若用户没有登陆，则会跳转到该页面
