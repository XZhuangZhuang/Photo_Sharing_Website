# -*- encoding=UTF-8 -*-

from Ch import app, db
from flask import render_template, redirect, request, flash, get_flashed_messages, send_from_directory
from models import Image, User,Comment
from flask_login import login_user, logout_user, current_user, login_required
import random, hashlib, json, uuid, os
from qiniusdk import qiniu_upload_file


# @app.route('/')
# def index():
#     images = Image.query.order_by('id desc').limit(10).all()
#     return render_template('index.html', images=images)
@app.route('/')
def index():
    # images = Image.query.order_by('id desc').limit(10).all()
    # 添加分页加载
    pagi = Image.query.order_by('id desc').paginate(page=1, per_page=10, error_out=False)
    return render_template('index.html', images=pagi.items, has_next=pagi.has_next)


# @app.route('/<int:page>/<int:per_page>/')
# def index_images(page, per_page):
#     pagi = Image.query.order_by('id desc').paginate(page=page, per_page=per_page, error_out=False)
#     map = {'has_next': pagi.has_next}
#     images = []
#     for image in pagi.items:
#         temp = {'id': image.id, 'url': image.url, 'comment_count': len(image.comments), 'user_id': image.user_id}
#         images.append(temp)
#     map['images'] = images
#     return json.dumps(map)


@app.route('/<int:page>/<int:per_page>/')
def index_images(page, per_page):
    paginate = Image.query.order_by(db.desc(Image.id)).paginate(page=page, per_page=per_page, error_out=False)
    map = {'has_next': paginate.has_next}
    images = []
    for image in paginate.items:
        comments = []
        for i in range(0, min(2, len(image.comments))):
            comment = image.comments[i]
            comments.append({'username': comment.user.username,
                             'user_id': comment.user_id,
                             'content': comment.content})
        imgvo = {'id': image.id,
                 'url': image.url,
                 'comment_count': len(image.comments),
                 'user_id': image.user_id,
                 'head_url': image.user.head_url,
                 'created_date': str(image.create_date),
                 'comments': comments}
        images.append(imgvo)

    map['images'] = images
    return json.dumps(map)


# @app.route('/index/addcomment/', methods={"post"})
# def add_indexcomment():
#     image_id = int(request.values['image_id'])
#     content = request.values['content']
#     comment = Comment(content, image_id, current_user.id)
#     db.session.add(comment)
#     db.session.commit()
#     return json.dumps({"code": 0, "id": comment.id,
#                        "content": comment.content,
#                        "username": comment.user.username,
#                        "user_id": comment.user_id})

@app.route('/image/<int:image_id>')
def image(image_id):
    image = Image.query.get(image_id)
    if image == None:
        return redirect('/')
    return render_template('pageDetail.html', image=image)


@app.route('/profile/<int:user_id>/')
@login_required  # 用户登陆该界面是需要登陆的
def profile(user_id):
    user = User.query.get(user_id)
    if user == None:
        return redirect('/')

    # 添加分页加载
    paginate = Image.query.filter_by(user_id=user_id).paginate(page=1, per_page=3, error_out=False)
    return render_template('profile.html', user=user, images=paginate.items, has_next=paginate.has_next)


@app.route('/profile/images/<int:user_id>/<int:page>/<int:per_page>/')
def user_images(user_id, page, per_page):
    paginate = Image.query.filter_by(user_id=user_id).paginate(page=page, per_page=per_page, error_out=False)

    map = {'has_next': paginate.has_next}
    images = []
    for image in paginate.items:
        temp = {'id': image.id, 'url': image.url, 'comment_count': len(image.comments)}
        images.append(temp)
    map['images'] = images
    return json.dumps(map)


@app.route('/regloginpage/')
def regloginpage():
    msg =''
    for m in get_flashed_messages(with_categories=False, category_filter=['reglogin']):
        msg = msg + m
    return render_template('login.html', msg=msg, next=request.values.get('next'))


@app.route('/login/', methods={'post', 'get'})
def login():
    username = request.values.get('username').strip()
    password = request.values.get('password').strip()

    if username == '' or password == '':
        flash(u'用户名和密码不能为空', category='reglogin')
        return redirect('/regloginpage/')

    user = User.query.filter_by(username=username).first()

    if user == None:
        flash(u'用户名不已经存在', category='reglogin')
        return redirect('/regloginpage/')

    m = hashlib.md5()
    m.update(password + user.salt)
    if m.hexdigest() != user.password:
        flash(u'密码错误', category='reglogin')
        return redirect('/regloginpage/')

    login_user(user)  # 用户登陆进来

    # next功能的跳转
    next = request.values.get('next')
    if next != None and next.startswith('/'):
        return redirect(next)
    return redirect('/')


@app.route('/reg/', methods={'post', 'get'})
def reg():
    username = request.values.get('username').strip()
    password = request.values.get('password').strip()

    if username == '' or password == '':
        flash(u'用户名和密码不能为空', category='reglogin')
        return redirect('/regloginpage/')

    user = User.query.filter_by(username=username).first()

    if user != None:
        flash(u'用户名已经存在', category='reglogin')
        return redirect('/regloginpage/')

    # 更多判断
    salt = '.'.join(random.sample('0123456789abcdefghigklmnABCDEFGHIJK', 10))
    m = hashlib.md5()
    m.update(password+salt)
    password = m.hexdigest()

    user = User(username, password, salt)
    db.session.add(user)
    db.session.commit()

    login_user(user)

    # next功能的跳转
    next = request.values.get('next')
    if next != None and next.startswith('/'):
        return redirect(next)

    return redirect('/')


@app.route('/logout/')
def logout():
    logout_user()
    return redirect('/')


def save_to_local(file, file_name):
    save_dir = app.config['UPLOAD_DIR']
    file.save(os.path.join(save_dir, file_name))
    return '/image/' + file_name


@app.route('/image/<image_name>')
def view_image(image_name):
    return send_from_directory(app.config['ALLOWED_EXT'], image_name)


@app.route('/upload/', methods={"post"})
def upload():
    file = request.files['file']
    file_exe = ''
    if file.filename.find('.') > 0:
        file_exe = file.filename.rsplit('.', 1)[1].strip().lower()
    if file_exe in app.config['ALLOWED_EXT']:
        file_name = str(uuid.uuid1()).replace('-', '') + '.' + file_exe
        # url = save_to_local(file, file_name)
        url = qiniu_upload_file(file, file_name)
        if url != None:
            db.session.add(Image(url, current_user.id))
            db.session.commit()
    return redirect('/profile/%d' % current_user.id)


@app.route('/addcomment/', methods={"post"})
def add_comment():
    image_id = int(request.values['image_id'])
    content = request.values['content']
    comment = Comment(content, image_id, current_user.id)
    db.session.add(comment)
    db.session.commit()
    return json.dumps({"code": 0, "id": comment.id,
                       "content": comment.content,
                       "username": comment.user.username,
                       "user_id": comment.user_id})