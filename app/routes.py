from datetime import datetime

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.urls import url_parse

from app import app, db
from app.forms import (
    CommentForm,
    EditProfileForm,
    LoginForm,
    PostForm,
    RegistrationForm,
    ResetPasswordRequestForm,
    ResetPasswordForm,
)
from app.models import Comment, Post, User, Vote
from app.mail import send_password_reset_email


# TODO upvote comments
# TODO delete comments
# TODO comment sort by score
# TODO login page does not redirect to previous (commenting example)
# TODO blueprints
# TODO review methods
# TODO prepare raw english version open sourced.


@app.route("/", methods=["GET", "POST"])
@app.route("/index", methods=["GET", "POST"])
def index():
    # TODO optimize this rendering
    for post in Post.query.filter_by(deleted=0).all():
        post.update()
        db.session.commit()

    page = request.args.get("page", 1, type=int)
    posts = (
        Post.query.filter_by(deleted=0)
        .order_by(Post.pop_score.desc())
        .limit(app.config["TOTAL_POSTS"])
        .from_self()
        .paginate(page, app.config["POSTS_PER_PAGE"], True)
    )

    start_rank_num = app.config["POSTS_PER_PAGE"] * (page - 1) + 1
    next_url = (
        url_for("index", page=posts.next_num) if posts.has_next else None
    )

    return render_template(
        "index.html",
        posts=posts.items,
        next_url=next_url,
        start_rank_num=start_rank_num,
    )


@app.route("/newest", methods=["GET", "POST"])
def new():
    for post in Post.query.all():
        post.update()
        db.session.commit()

    page = request.args.get("page", 1, type=int)
    posts = (
        Post.query.filter_by(deleted=0)
        .order_by(Post.timestamp.desc())
        .paginate(page, app.config["POSTS_PER_PAGE"], True)
    )

    start_rank_num = app.config["POSTS_PER_PAGE"] * (page - 1) + 1
    next_url = url_for("new", page=posts.next_num) if posts.has_next else None

    return render_template(
        "index.html",
        posts=posts.items,
        next_url=next_url,
        start_rank_num=start_rank_num,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash("Invalid username or password")
            return redirect(url_for("login"))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get("next")
        if not next_page or url_parse(next_page).netloc != "":
            next_page = url_for("index")
        return redirect(next_page)
    return render_template("login.html", title="Sign In", form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Congratulations, you are now a registered user!")
        return redirect(url_for("login"))
    return render_template("register.html", title="Register", form=form)


@app.route("/user/<username>", methods=["GET"])
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template(
        "user.html", user=user, title=f"Profile: {username}"
    )


@app.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username, current_user.email)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        current_user.email = form.email.data
        db.session.commit()
        flash("Your changes have been saved.")
        return redirect(url_for("edit_profile"))
    elif request.method == "GET":
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
        form.email.data = current_user.email
    return render_template(
        "edit_profile.html", title="Edit Profile", form=form
    )


@app.route("/submit", methods=["GET", "POST"])
@login_required
def submit():
    form = PostForm()
    if form.validate_on_submit():
        if current_user.can_post():
            post = Post(
                title=form.title.data,
                url=form.url.data,
                text=form.text.data,
                author=current_user,
            )
            post.format_post(form.url.data)
            db.session.add(post)
            db.session.commit()
            flash("Congratulations, your post was published!")
            return redirect(url_for("post_page", post_id=post.id))
        else:
            flash(
                f"Sorry, you can only post {app.config['USER_POSTS_PER_DAY']} times a day"
            )
            return redirect(url_for("index"))

    return render_template("submit.html", title="Submit", form=form)


@app.route("/upvote/<post_id>", methods=["GET"])
@login_required
def upvote(post_id):
    post_to_upvote = Post.query.filter_by(id=post_id).first_or_404()
    vote_query = Vote.query.filter_by(
        user_id=current_user.id, post_id=post_to_upvote.id
    ).first()
    if vote_query is not None:
        return redirect(url_for("index"))
    else:
        post_to_upvote.score += 1
        post_to_upvote.author.karma += 1
        vote = Vote(user_id=current_user.id, post_id=post_to_upvote.id)
        db.session.add(vote)
        db.session.commit()
        return redirect(url_for("index"))


@app.route("/delete/<post_id>", methods=["GET"])
@login_required
def delete(post_id):
    post = Post.query.filter_by(id=post_id).first_or_404()
    if current_user == post.author:
        post.delete_post()
        db.session.commit()
        return redirect(url_for("index"))
    else:
        return render_template("404.html"), 404


@app.route("/post/<post_id>", methods=["GET", "POST"])
def post_page(post_id):
    post = Post.query.filter_by(id=post_id).first_or_404()

    comments = (
        Comment.query.filter_by(post_id=post.id)
        .order_by(Comment.thread_timestamp.desc(), Comment.path.asc())
        .all()
    )
    form = CommentForm()
    if form.validate_on_submit():
        if current_user.is_authenticated:
            if current_user.can_comment():
                comment = Comment(
                    text=form.text.data,
                    author=current_user,
                    post_id=post.id,
                    timestamp=datetime.utcnow(),
                    thread_timestamp=datetime.utcnow(),
                )
                comment.save()
                return redirect(url_for("post_page", post_id=post.id))
            else:
                flash(
                    f"You can only commment {app.config['USER_COMMENTS_PER_DAY']} times a day."
                )
        else:
            return redirect(url_for("login"))

    return render_template(
        "post.html", post=post, form=form, comments=comments, title=post.title
    )


@app.route("/submissions/<username>", methods=["GET"])
def user_submissions(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user, deleted=0).order_by(
        Post.timestamp.desc()
    )
    return render_template("index.html", posts=posts)


@app.route("/reply/<comment_id>", methods=["GET", "POST"])
@login_required
def reply(comment_id):
    parent = Comment.query.filter_by(id=comment_id).first_or_404()
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(
            text=form.text.data,
            author=current_user,
            post_id=parent.post_id,
            parent_id=parent.id,
            timestamp=datetime.utcnow(),
            thread_timestamp=parent.thread_timestamp,
        )
        comment.save()
        return redirect(url_for("post_page", post_id=parent.post_id))
    return render_template("reply.html", comment=parent, form=form)


@app.route("/reset_password_request", methods=["GET", "POST"])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash("An email with instructions was sent to your address.")
        return redirect(url_for("login"))
    return render_template(
        "reset_password_request.html", title="Reset Password", form=form
    )


@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for("index"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash("Your password has been reset.")
        return redirect(url_for("login"))
    return render_template("reset_password.html", form=form)
