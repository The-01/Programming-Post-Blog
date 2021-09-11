from flask import Flask, render_template, request, session, redirect
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from flask_mail import Mail
import json
import os
import math
from datetime import datetime


with open("config.json", "r") as json_file:
    params = json.load(json_file)["params"]

local_server = True
app = Flask(__name__, template_folder="template")
app.secret_key = 'abaaqa'
app.config['UPLOAD_FOLDER'] = params['upload_location']
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT='465',
    MAIL_USE_SSL=True,
    MAIL_USERNAME=params['gmail_id'],
    MAIL_PASSWORD=params['gmail_password']
)
mail = Mail(app)
if local_server:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['local_uri']
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['production_uri']

db = SQLAlchemy(app)


class Contacts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(30), nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)
    message = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(15), nullable=True)


class Posts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    subtitle = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(25), nullable=False)
    content = db.Column(db.String(120), nullable=False)
    img_file = db.Column(db.String(50), nullable=False)
    posted_by = db.Column(db.String(50), nullable=False)
    date = db.Column(db.String(15), nullable=True)


@app.route("/")
def home():
    posts = Posts.query.filter_by().all()

    # Pagination Logic
    page = request.args.get("page")
    first_page = 1
    last_page = math.ceil(len(posts) / params['no_of_posts'])
    if not str(page).isnumeric():
        page = first_page
    page = int(page)

    posts = posts[(page-1)*params['no_of_posts']:(page-1)*params['no_of_posts']+params['no_of_posts']]
    if page == first_page:
        prev = "#"
        next = "/?page=" + str(page+1)
    elif page == last_page:
        prev = "/?page=" + str(page-1)
        next = "#"
    else:
        prev = "/?page=" + str(page-1)
        next = "/?page=" + str(page+1)

    return render_template('index.html', params=params, posts=posts, prev=prev, next=next)


@app.route("/about")
def about():
    return render_template('about.html', params=params)


@app.route("/dashboard", methods=['GET', 'POST'])
def dashboard():
    if 'user' in session and session['user'] == params['admin_username']:
        posts = Posts.query.all()
        return render_template('dashboard.html', params=params, posts = posts)

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == params['admin_username'] and password == params['admin_password']:
            # set the session variable
            session['user'] = username
            posts = Posts.query.all()
            return render_template('dashboard.html', params=params, posts=posts)

    return render_template('login.html', params=params)


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == 'POST':
        _name = request.form.get("name")
        _email = request.form.get("email")
        _phone_number = request.form.get("phone_number")
        _message = request.form.get("message")
        entry = Contacts(name=_name, email=_email, phone_number=_phone_number, message=_message, date=datetime.now())
        db.session.add(entry)
        db.session.commit()
        mail.send_message(
            f"New message from {_name}",
            sender=_email,
            recipients=[params["gmail_id"]],
            body=f"{_message}\nMy gmail id: {_email}\nMy phone number: {_phone_number}"
        )

    return render_template('contact.html', params=params)


@app.route("/post/<string:post_slug>", methods=['GET'])
def post(post_slug):
    _post = Posts.query.filter_by(slug=post_slug).first()
    return render_template('post.html', params=params, post=_post)


@app.route("/logout")
def logout():
    session.pop('user', None)
    return redirect("/dashboard")


@app.route("/edit/<string:sno>", methods=['GET', 'POST'])
def edit(sno):
    if 'user' in session and session['user'] == params['admin_username']:
        if request.method == 'POST':
            _title = request.form.get('title')
            _subtitle = request.form.get('subtitle')
            _slug = request.form.get('slug')
            _content = request.form.get('content')
            _img_file = request.form.get('img_file')
            _posted_by = request.form.get('posted_by')
            _date = datetime.now()

            if sno == '0':
                _post = Posts(title=_title, slug=_slug, content=_content, subtitle=_subtitle, img_file=_img_file,
                              posted_by=_posted_by, date=_date)
                db.session.add(_post)
                db.session.commit()
            else:
                _post = Posts.query.filter_by(sno=sno).first()
                _post.title = _title
                _post.slug = _slug
                _post.content = _content
                _post.subtitle = _subtitle
                _post.img_file = _img_file
                _post.posted_by = _posted_by
                _post.date = _date
                db.session.commit()
                return redirect('/edit/'+sno)

        _post = Posts.query.filter_by(sno=sno).first()
        return render_template('edit.html', params=params, post=_post, sno=sno)


@app.route("/delete/<string:sno>", methods=['GET', 'POST'])
def delete(sno):
    if 'user' in session and session['user'] == params['admin_username']:
        _post = Posts.query.filter_by(sno=sno).first()
        db.session.delete(_post)
        db.session.commit()
    return redirect("/dashboard")


@app.route("/uploader", methods=['GET', 'POST'])
def uploader():
    if request.method == 'POST':
        f = request.files['file']
        f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))
        return redirect("/dashboard")


if __name__ == '__main__':
    app.run(debug=True)

