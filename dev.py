from app import app, db
from app.models import User, Post, Vote, Comment, Comment_Vote


@app.shell_context_processor
def make_shell_context():
    return {
        "db": db,
        "User": User,
        "Post": Post,
        "Vote": Vote,
        "Comment": Comment,
        "Comment_Vote": Comment_Vote,
    }
