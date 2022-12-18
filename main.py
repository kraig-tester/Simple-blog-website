from flask import Flask, flash, render_template, redirect, url_for, request, abort
from flask_bootstrap import Bootstrap
from flask_gravatar import Gravatar
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask_ckeditor import CKEditor, CKEditorField
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
import datetime as dt
import bleach

app = Flask(__name__)

app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class BlogPost(db.Model):
    __tablename__ = "posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    author = db.relationship("User", back_populates="posts")
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    img_url = db.Column(db.String(250), nullable=False)
    comments = db.relationship("Comment", back_populates="post")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    author = db.relationship("User", back_populates="comments")
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post = db.relationship("BlogPost", back_populates="comments")
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    posts = db.relationship("BlogPost", back_populates="author")
    comments = db.relationship("Comment", back_populates="author")

    def __repr__(self) -> str:
        return self.name
        

with app.app_context():
    db.create_all()


def strip_invalid_html(content):
    allowed_tags = ['a', 'abbr', 'acronym', 'address', 'b', 'br', 'div', 'dl', 'dt',
                    'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img',
                    'li', 'ol', 'p', 'pre', 'q', 's', 'small', 'strike',
                    'span', 'sub', 'sup', 'table', 'tbody', 'td', 'tfoot', 'th',
                    'thead', 'tr', 'tt', 'u', 'ul']
 
    allowed_attrs = {
        'a': ['href', 'target', 'title'],
        'img': ['src', 'alt', 'width', 'height'],
    }
 
    cleaned = bleach.clean(content,
                           tags=allowed_tags,
                           attributes=allowed_attrs,
                           strip=True)
 
    return cleaned


def admin_only(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.id != 1:
            return abort(403)
        return func(*args, **kwargs) 
    return wrapper


@app.route('/')
@app.route('/index.html')
def home():
    all_posts = db.session.query(BlogPost).all()
    return render_template('index.html', all_posts=all_posts)


@app.route('/new-post', methods=['GET', 'POST'])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if request.method=='POST':
        today=dt.datetime.today()
        new_post = BlogPost(
            title=request.form.get("title"),
            subtitle=request.form.get("subtitle"),
            date=today.strftime("%B %d, %Y"),
            author=current_user,
            img_url=request.form.get("img_url"),
            body=strip_invalid_html(request.form.get("body"))
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('home'))    
    return render_template('add.html', form=form)


@app.route('/edit-post/<post_id>', methods=['GET', 'POST'])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
        
    if request.method=='POST':
        post.title = request.form.get("title")
        post.subtitle = request.form.get("subtitle")
        post.img_url = request.form.get("img_url")
        post.author = request.form.get("author")
        post.body = request.form.get("body")

        db.session.commit()
        return redirect(url_for('home'))

    form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    return render_template('add.html', form=form)


@app.route('/delete/<post_id>')
@admin_only
def delete_post(post_id):
    post = BlogPost.query.get(post_id)
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for('home'))


@app.route('/about.html')
def about():
    return render_template('about.html')


@app.route('/contact.html', methods=["GET", "POST"])
def contact():
    if request.method=="POST":
        return render_template('contact.html', message="Successfully sent your message!")
    return render_template('contact.html', message="Contact me")


@app.route('/post/<id>.html', methods=["GET", "POST"])
def post(id):
    all_posts = db.session.query(BlogPost).all()
    current_post = all_posts[int(id)-1]
    comment_form = CommentForm()
    if request.method == "POST":
        if not current_user.is_authenticated:
            flash("You should be authenticated in order to leave comments.")
            return redirect(url_for("login"))

        new_comment = Comment(
            text = request.form.get("body"),
            author = current_user,
            post = current_post
        )

        db.session.add(new_comment)
        db.session.commit()

    return render_template('post.html', post=current_post, form=comment_form)


@app.route('/register', methods=["GET", "POST"])
def register():
    '''Added some documentation'''
    register_form = RegisterForm()
    if request.method == "POST":
        user = User.query.filter_by(email=request.form.get("email")).first()

        if not user:
            flash("User with this email already exists.")
            return render_template("register.html", form=register_form)

        new_user = User(
            email=request.form.get("email"),
            name=request.form.get("name"),
            password=generate_password_hash(password=request.form.get("password"), salt_length=8)
        )
        
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)

        return redirect(url_for('home'))
        
    return render_template("register.html", form=register_form)


@app.route('/login', methods=["GET", "POST"])
def login():
    login_form = LoginForm()
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user:
            flash("User does not exist.")
        elif check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash("Incorrect password.")
        
    return render_template('login.html', form=login_form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)