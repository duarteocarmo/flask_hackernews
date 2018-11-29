from datetime import datetime

from flask import (
    flash,
    redirect,
    render_template,
    request,
    url_for,
    current_app,
)
from flask_login import current_user, login_required

from app import db
from app.main.forms import CommentForm, EditProfileForm, PostForm
from app.models import Comment, Post, User, Vote, Comment_Vote
from app.main import bp

# TODO post filtering by source
# TODO fix rankings
# TODO page titles
# TODO report 


def redirect_url(default="main.index"):
    return request.args.get("next") or request.referrer or url_for(default)


@bp.route("/", methods=["GET"])
@bp.route("/index", methods=["GET"])
def index():
    # TODO optimize this rendering
    for post in Post.query.filter_by(deleted=0).all():
        post.update()
        db.session.commit()

    page = request.args.get("page", 1, type=int)
    posts = (
        Post.query.filter_by(deleted=0)
        .order_by(Post.pop_score.desc())
        .limit(current_app.config["TOTAL_POSTS"])
        .from_self()
        .paginate(page, current_app.config["POSTS_PER_PAGE"], True)
    )

    start_rank_num = current_app.config["POSTS_PER_PAGE"] * (page - 1) + 1
    next_url = (
        url_for("main.index", page=posts.next_num) if posts.has_next else None
    )

    return render_template(
        "index.html",
        posts=posts.items,
        next_url=next_url,
        start_rank_num=start_rank_num,
    )


@bp.route("/newest", methods=["GET"])
def new():
    for post in Post.query.all():
        post.update()
        db.session.commit()

    page = request.args.get("page", 1, type=int)
    posts = (
        Post.query.filter_by(deleted=0)
        .order_by(Post.timestamp.desc())
        .paginate(page, current_app.config["POSTS_PER_PAGE"], True)
    )

    start_rank_num = current_app.config["POSTS_PER_PAGE"] * (page - 1) + 1
    next_url = (
        url_for("main.new", page=posts.next_num) if posts.has_next else None
    )

    return render_template(
        "index.html",
        posts=posts.items,
        next_url=next_url,
        start_rank_num=start_rank_num,
    )


@bp.route("/user/<username>", methods=["GET"])
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template(
        "user.html", user=user, title=f"Profile: {username}"
    )


@bp.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username, current_user.email)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        current_user.email = form.email.data
        db.session.commit()
        flash("Guardámos as tuas edições.")
        return redirect(url_for("main.edit_profile"))
    elif request.method == "GET":
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
        form.email.data = current_user.email
    return render_template(
        "edit_profile.html", title="Edit Profile", form=form
    )


@bp.route("/submit", methods=["GET", "POST"])
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
            flash("Parabéns! O teu post foi publicado!")
            return redirect(url_for("main.post_page", post_id=post.id))
        else:
            flash(
                f"Desculpa, só podes postar {current_app.config['USER_POSTS_PER_DAY']} vezes por dia."
            )
            return redirect(url_for("main.index"))

    return render_template("submit.html", title="Submit", form=form)


@bp.route("/post/<post_id>", methods=["GET", "POST"])
def post_page(post_id):
    post = Post.query.filter_by(id=post_id).first_or_404()

    comments = (
        Comment.query.filter_by(post_id=post.id)
        # .order_by(Comment.thread_timestamp.desc(), Comment.path.asc())
        .order_by(Comment.thread_score.desc(), Comment.path.asc()).all()
    )
    form = CommentForm()
    if form.validate_on_submit():
        print("HERE")
        if current_user.is_authenticated:
            if current_user.can_comment():
                print("HERE")
                comment = Comment(
                    text=form.text.data,
                    author=current_user,
                    post_id=post.id,
                    timestamp=datetime.utcnow(),
                    thread_timestamp=datetime.utcnow(),
                )
                comment.save()
                return redirect(url_for("main.post_page", post_id=post.id))
            else:
                flash(
                    f"Só podes comentar {current_app.config['USER_COMMENTS_PER_DAY']} vezes por dia."
                )
        else:
            return redirect(url_for("auth.login"))

    return render_template(
        "post.html", post=post, form=form, comments=comments, title=post.title
    )


@bp.route("/upvote/<post_id>", methods=["GET"])
@login_required
def upvote(post_id):
    post_to_upvote = Post.query.filter_by(id=post_id).first_or_404()
    vote_query = Vote.query.filter_by(
        user_id=current_user.id, post_id=post_to_upvote.id
    ).first()
    if vote_query is not None:
        flash("Já votaste neste post")
    else:
        post_to_upvote.update_votes()
        vote = Vote(user_id=current_user.id, post_id=post_to_upvote.id)
        db.session.add(vote)
        db.session.commit()

    return redirect(redirect_url())


@bp.route("/delete/post/<post_id>", methods=["GET"])
@login_required
def delete_post(post_id):
    post = Post.query.filter_by(id=post_id).first_or_404()
    if current_user == post.author:
        post.delete_post()
        db.session.commit()
        return redirect(redirect_url())
    else:
        return render_template("404.html"), 404


@bp.route("/delete/comment/<comment_id>", methods=["GET"])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.filter_by(id=comment_id).first_or_404()
    if current_user == comment.author:
        comment.text = "[Deleted]"
        db.session.commit()
        return redirect(redirect_url())
    else:
        return render_template("404.html"), 404


@bp.route("/submissions/<username>", methods=["GET"])
def user_submissions(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user, deleted=0).order_by(
        Post.timestamp.desc()
    )
    return render_template("index.html", posts=posts)


@bp.route("/reply/<comment_id>", methods=["GET", "POST"])
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
        return redirect(url_for("main.post_page", post_id=parent.post_id))
    return render_template("reply.html", comment=parent, form=form)


@bp.route("/upvote_comment/<comment_id>", methods=["GET"])
@login_required
def upvote_comment(comment_id):
    comment_to_upvote = Comment.query.filter_by(id=comment_id).first_or_404()
    vote_query = Comment_Vote.query.filter_by(
        user_id=current_user.id, comment_id=comment_to_upvote.id
    ).first()
    if vote_query is not None:
        flash("Já votaste neste comentário.")
    else:
        comment_to_upvote.update_votes()
        vote = Comment_Vote(
            user_id=current_user.id, comment_id=comment_to_upvote.id
        )
        db.session.add(vote)
        db.session.commit()

    return redirect(redirect_url())
